
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st.set_page_config(page_title="SPY vs DIA Dual Mode Dashboard", layout="wide")

# Dynamic button styling
if "running" not in st.session_state:
    st.session_state.running = False

run_color = "#00cc66" if st.session_state.running else "#444444"
stop_color = "#ff3333" if not st.session_state.running else "#444444"

st.markdown(f"""
<style>
div.stButton > button:first-child {{
    border-radius: 10px;
    height: 3em;
    font-weight: bold;
}}

div[data-testid="column"]:nth-of-type(1) button {{
    background-color: {run_color};
    color: white;
}}

div[data-testid="column"]:nth-of-type(2) button {{
    background-color: {stop_color};
    color: white;
}}
</style>
""", unsafe_allow_html=True)

st.title("SPY vs DIA Dual Mode Dashboard")
st.caption("Pattern dashboard + separate 1-second live trading view.")

if "view_period" not in st.session_state:
    st.session_state.view_period = "1d"

if "interval" not in st.session_state:
    st.session_state.interval = "1m"

if "mode" not in st.session_state:
    st.session_state.mode = "Pattern Dashboard"

st.sidebar.header("Dashboard Mode")

mode = st.sidebar.radio(
    "Choose view",
    ["Pattern Dashboard", "1-Second Trading View"]
)

st.session_state.mode = mode

st.subheader("Controls")

col_run, col_stop, col_day, col_5day, col_month = st.columns(5)

with col_run:
    if st.button("▶ RUN LIVE", use_container_width=True):
        st.session_state.running = True
        st.rerun()

with col_stop:
    if st.button("■ STOP", use_container_width=True):
        st.session_state.running = False
        st.rerun()

with col_day:
    if st.button("TODAY", use_container_width=True):
        st.session_state.view_period = "1d"
        st.session_state.interval = "1m"

with col_5day:
    if st.button("5 DAY", use_container_width=True):
        st.session_state.view_period = "5d"
        st.session_state.interval = "5m"

with col_month:
    if st.button("1 MONTH", use_container_width=True):
        st.session_state.view_period = "1mo"
        st.session_state.interval = "15m"

refresh_seconds = st.sidebar.slider("Refresh Speed", 1, 5, 1)

if st.session_state.running:
    st_autorefresh(interval=refresh_seconds * 1000, key="refresh")

@st.cache_data(ttl=1)
def load_data(period, interval):
    spy = yf.download("SPY", period=period, interval=interval, progress=False, auto_adjust=True)
    dia = yf.download("DIA", period=period, interval=interval, progress=False, auto_adjust=True)
    return spy, dia

spy, dia = load_data(st.session_state.view_period, st.session_state.interval)

def clean_close(df):
    close_series = df["Close"]

    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]

    return pd.to_numeric(close_series, errors="coerce").dropna()

spy_close = clean_close(spy)
dia_close = clean_close(dia)

spy_latest = float(spy_close.iloc[-1])
spy_prev = float(spy_close.iloc[-2])

dia_latest = float(dia_close.iloc[-1])
dia_prev = float(dia_close.iloc[-2])

spy_change = spy_latest - spy_prev
dia_change = dia_latest - dia_prev

status = "LIVE RUNNING" if st.session_state.running else "PAUSED"

st.info(f"Status: {status}")

m1, m2 = st.columns(2)

with m1:
    st.metric("SPY", f"${spy_latest:.2f}", f"{spy_change:.2f}")

with m2:
    st.metric("DIA", f"${dia_latest:.2f}", f"{dia_change:.2f}")

# Joined chart
joined = pd.concat(
    [spy_close.rename("SPY"), dia_close.rename("DIA")],
    axis=1
).dropna()

joined["SPY Pattern"] = (joined["SPY"] / joined["SPY"].iloc[0] - 1) * 100
joined["DIA Pattern"] = (joined["DIA"] / joined["DIA"].iloc[0] - 1) * 100

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=joined.index,
    y=joined["SPY Pattern"],
    mode="lines",
    name="SPY Pattern"
))

fig.add_trace(go.Scatter(
    x=joined.index,
    y=joined["DIA Pattern"],
    mode="lines",
    name="DIA Pattern"
))

fig.update_layout(
    height=600,
    template="plotly_dark",
    title="Joined SPY vs DIA Pattern Chart",
    hovermode="x unified"
)

st.plotly_chart(fig, use_container_width=True)

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
