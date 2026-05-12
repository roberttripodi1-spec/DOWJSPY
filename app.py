
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st.set_page_config(page_title="SPY vs DIA Live Dashboard", layout="wide")

st.title("SPY vs DIA Live Dashboard")
st.caption("Live market proxy dashboard for S&P 500 and Dow Jones")

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
    try:
        spy = yf.download("SPY", period="1d", interval="1m", progress=False, auto_adjust=True)
        dia = yf.download("DIA", period="1d", interval="1m", progress=False, auto_adjust=True)

        if spy.empty or dia.empty:
            return None, None

        return spy, dia

    except Exception as e:
        st.error(f"Data error: {e}")
        return None, None


def get_close_values(df):
    try:
        close_series = df["Close"]

        # Handle dataframe case from yfinance
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]

        close_series = pd.to_numeric(close_series, errors="coerce").dropna()

        if len(close_series) < 2:
            return None, None

        latest = float(close_series.iloc[-1])
        previous = float(close_series.iloc[-2])

        return latest, previous

    except Exception:
        return None, None


spy, dia = load_data()

if spy is None or dia is None:
    st.warning("Market data unavailable right now.")
    st.stop()

spy_latest, spy_prev = get_close_values(spy)
dia_latest, dia_prev = get_close_values(dia)

if spy_latest is None or dia_latest is None:
    st.warning("Not enough market data yet.")
    st.stop()

spy_change = spy_latest - spy_prev
dia_change = dia_latest - dia_prev

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

    st.metric(
        "SPY Last Price",
        f"${spy_latest:.2f}",
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

    st.metric(
        "DIA Last Price",
        f"${dia_latest:.2f}",
        f"{dia_change:.2f}"
    )

st.divider()

snapshot = pd.DataFrame({
    "Ticker": ["SPY", "DIA"],
    "Last Price": [spy_latest, dia_latest],
    "1-Min Change": [spy_change, dia_change]
})

st.subheader("Market Snapshot")
st.dataframe(snapshot, use_container_width=True)

status = "LIVE RUNNING" if st.session_state.running else "PAUSED"

st.caption(f"Status: {status}")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
