
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st.set_page_config(page_title="SPY vs DIA Live Dashboard", layout="wide")

st.title("SPY vs DIA Live Dashboard")
st.caption("Live market proxy dashboard for S&P 500 and Dow Jones")

# Session state for live mode
if "running" not in st.session_state:
    st.session_state.running = False

col_run, col_stop = st.columns(2)

with col_run:
    if st.button("▶ RUN LIVE"):
        st.session_state.running = True

with col_stop:
    if st.button("■ STOP"):
        st.session_state.running = False

refresh_seconds = st.sidebar.slider("Refresh Interval (seconds)", 1, 10, 1)

if st.session_state.running:
    st_autorefresh(interval=refresh_seconds * 1000, key="refresh")

@st.cache_data(ttl=1)
def load_data():
    spy = yf.download("SPY", period="1d", interval="1m", progress=False)
    dia = yf.download("DIA", period="1d", interval="1m", progress=False)
    return spy, dia

spy, dia = load_data()

col1, col2 = st.columns(2)

with col1:
    st.subheader("SPY (S&P 500 Proxy)")

    fig1 = go.Figure()
    fig1.add_trace(go.Scatter(
        x=spy.index,
        y=spy["Close"],
        mode="lines",
        name="SPY"
    ))

    fig1.update_layout(
        height=500,
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark"
    )

    st.plotly_chart(fig1, use_container_width=True)

    latest_spy = float(spy["Close"].iloc[-1])
    prev_spy = float(spy["Close"].iloc[-2])
    spy_change = latest_spy - prev_spy

    st.metric(
        "SPY Last Price",
        f"${latest_spy:.2f}",
        f"{spy_change:.2f}"
    )

with col2:
    st.subheader("DIA (Dow Jones Proxy)")

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=dia.index,
        y=dia["Close"],
        mode="lines",
        name="DIA"
    ))

    fig2.update_layout(
        height=500,
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark"
    )

    st.plotly_chart(fig2, use_container_width=True)

    latest_dia = float(dia["Close"].iloc[-1])
    prev_dia = float(dia["Close"].iloc[-2])
    dia_change = latest_dia - prev_dia

    st.metric(
        "DIA Last Price",
        f"${latest_dia:.2f}",
        f"{dia_change:.2f}"
    )

st.divider()

st.subheader("Market Snapshot")

snapshot = pd.DataFrame({
    "Ticker": ["SPY", "DIA"],
    "Last Price": [latest_spy, latest_dia],
    "1-Min Change": [spy_change, dia_change]
})

st.dataframe(snapshot, use_container_width=True)

status = "LIVE RUNNING" if st.session_state.running else "PAUSED"

st.caption(f"Status: {status}")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
