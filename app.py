import os
import json
import time
import queue
import threading
from collections import deque
from datetime import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import websocket

st.set_page_config(page_title="S&P + Dow 1-Second Dashboard", layout="wide")
st.title("S&P 500 + Dow Jones — 1-Second Live Dashboard")
st.caption("Designed for fast day-trading reads. Use SPY/DIA for ETF proxies or Polygon index symbols if your plan supports them.")

# -----------------------------
# Sidebar controls
# -----------------------------
api_key = st.sidebar.text_input(
    "Polygon API Key",
    value=os.getenv("POLYGON_API_KEY", ""),
    type="password",
    help="Create a POLYGON_API_KEY environment variable or paste it here."
)

feed_type = st.sidebar.selectbox(
    "Feed type",
    ["Stocks/ETFs", "Indices"],
    index=0,
    help="Stocks/ETFs: use SPY and DIA. Indices: use I:SPX and I:DJI if your Polygon plan supports index second aggregates."
)

if feed_type == "Stocks/ETFs":
    default_left, default_right = "SPY", "DIA"
    ws_url = "wss://socket.polygon.io/stocks"
    sub_prefix = "A."  # second aggregates for stocks/ETFs
else:
    default_left, default_right = "I:SPX", "I:DJI"
    ws_url = "wss://socket.polygon.io/indices"
    sub_prefix = "A."

symbol_left = st.sidebar.text_input("Left symbol", default_left).upper().strip()
symbol_right = st.sidebar.text_input("Right symbol", default_right).upper().strip()
window_seconds = st.sidebar.slider("Chart window, seconds", 30, 1800, 300, step=30)
refresh_ms = st.sidebar.slider("Screen refresh, milliseconds", 250, 2000, 1000, step=250)
normalize = st.sidebar.checkbox("Normalize both lines to % move", value=True)

st.sidebar.markdown("---")
st.sidebar.write("Recommended: SPY + DIA for reliable ETF trading data. True index symbols may require a paid index feed.")

if not api_key:
    st.warning("Enter your Polygon API key in the sidebar to start streaming.")
    st.stop()

# -----------------------------
# Streamlit session state
# -----------------------------
if "ticks" not in st.session_state:
    st.session_state.ticks = {
        symbol_left: deque(maxlen=5000),
        symbol_right: deque(maxlen=5000),
    }
if "message_queue" not in st.session_state:
    st.session_state.message_queue = queue.Queue()
if "stream_key" not in st.session_state:
    st.session_state.stream_key = None
if "status" not in st.session_state:
    st.session_state.status = "Not connected"

stream_key = f"{feed_type}|{symbol_left}|{symbol_right}"

# Reset if symbols/feed changed
if st.session_state.stream_key != stream_key:
    st.session_state.ticks = {
        symbol_left: deque(maxlen=5000),
        symbol_right: deque(maxlen=5000),
    }
    st.session_state.message_queue = queue.Queue()
    st.session_state.stream_key = stream_key
    st.session_state.status = "Connecting"

# -----------------------------
# WebSocket thread
# -----------------------------
def start_polygon_stream(api_key: str, url: str, symbols: list[str], output_queue: queue.Queue):
    def on_open(ws):
        ws.send(json.dumps({"action": "auth", "params": api_key}))
        params = ",".join([f"{sub_prefix}{s}" for s in symbols])
        ws.send(json.dumps({"action": "subscribe", "params": params}))
        output_queue.put({"type": "status", "value": f"Subscribed to {params}"})

    def on_message(ws, message):
        try:
            data = json.loads(message)
        except Exception:
            return
        if not isinstance(data, list):
            return
        for item in data:
            ev = item.get("ev")
            if ev == "status":
                output_queue.put({"type": "status", "value": item.get("message", "status")})
                continue
            # Polygon aggregate fields commonly include sym, c, o, h, l, v, s/e timestamps
            if ev == "A":
                sym = item.get("sym")
                close = item.get("c")
                ts = item.get("e") or item.get("s")
                if sym and close is not None and ts:
                    output_queue.put({
                        "type": "bar",
                        "symbol": sym,
                        "close": float(close),
                        "time": datetime.fromtimestamp(ts / 1000),
                        "open": item.get("o"),
                        "high": item.get("h"),
                        "low": item.get("l"),
                        "volume": item.get("v"),
                    })

    def on_error(ws, error):
        output_queue.put({"type": "status", "value": f"WebSocket error: {error}"})

    def on_close(ws, close_status_code, close_msg):
        output_queue.put({"type": "status", "value": f"Closed: {close_status_code} {close_msg}"})

    ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
    ws.run_forever(ping_interval=20, ping_timeout=10)

thread_name = f"polygon_thread_{stream_key}"
if thread_name not in st.session_state:
    t = threading.Thread(
        target=start_polygon_stream,
        args=(api_key, ws_url, [symbol_left, symbol_right], st.session_state.message_queue),
        daemon=True,
    )
    t.start()
    st.session_state[thread_name] = True

# Pull queued messages into state
while not st.session_state.message_queue.empty():
    msg = st.session_state.message_queue.get()
    if msg["type"] == "status":
        st.session_state.status = msg["value"]
    elif msg["type"] == "bar":
        sym = msg["symbol"]
        if sym not in st.session_state.ticks:
            st.session_state.ticks[sym] = deque(maxlen=5000)
        st.session_state.ticks[sym].append(msg)

# -----------------------------
# Data prep
# -----------------------------
def make_df(symbol: str) -> pd.DataFrame:
    rows = list(st.session_state.ticks.get(symbol, []))
    if not rows:
        return pd.DataFrame(columns=["time", "close", "open", "high", "low", "volume", "symbol"])
    df = pd.DataFrame(rows)
    cutoff = datetime.now() - pd.Timedelta(seconds=window_seconds)
    df = df[df["time"] >= cutoff].copy()
    df["symbol"] = symbol
    return df

df_left = make_df(symbol_left)
df_right = make_df(symbol_right)

# -----------------------------
# Top metrics
# -----------------------------
col1, col2, col3 = st.columns([1, 1, 2])

def last_and_change(df):
    if df.empty:
        return None, None
    last = df["close"].iloc[-1]
    first = df["close"].iloc[0]
    pct = ((last / first) - 1) * 100 if first else 0
    return last, pct

left_last, left_pct = last_and_change(df_left)
right_last, right_pct = last_and_change(df_right)

col1.metric(symbol_left, "—" if left_last is None else f"{left_last:,.2f}", None if left_pct is None else f"{left_pct:+.3f}%")
col2.metric(symbol_right, "—" if right_last is None else f"{right_last:,.2f}", None if right_pct is None else f"{right_pct:+.3f}%")
col3.info(f"Status: {st.session_state.status}")

# -----------------------------
# Chart
# -----------------------------
fig = go.Figure()

for sym, df in [(symbol_left, df_left), (symbol_right, df_right)]:
    if df.empty:
        continue
    y = df["close"]
    y_title = "Price"
    if normalize and len(df) > 0 and df["close"].iloc[0] != 0:
        y = ((df["close"] / df["close"].iloc[0]) - 1) * 100
        y_title = "% Move From Window Start"
    fig.add_trace(go.Scatter(x=df["time"], y=y, mode="lines", name=sym))

fig.update_layout(
    height=650,
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis_title="Time",
    yaxis_title=y_title if normalize else "Price",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
st.plotly_chart(fig, use_container_width=True)

# Latest rows for fast tape read
combined = pd.concat([df_left.tail(5), df_right.tail(5)], ignore_index=True)
if not combined.empty:
    combined = combined.sort_values("time", ascending=False)[["time", "symbol", "close", "open", "high", "low", "volume"]]
    st.dataframe(combined, use_container_width=True, hide_index=True)

# Auto refresh
st.markdown(f"<meta http-equiv='refresh' content='{refresh_ms/1000}'>", unsafe_allow_html=True)
