
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

st.set_page_config(page_title="SPY vs DIA Dual Mode Dashboard", layout="wide")

st.title("SPY vs DIA Dual Mode Dashboard")
st.caption("Pattern dashboard + separate 1-second live trading view.")

if "running" not in st.session_state:
    st.session_state.running = False

if "view_period" not in st.session_state:
    st.session_state.view_period = "1d"

if "interval" not in st.session_state:
    st.session_state.interval = "1m"

if "mode" not in st.session_state:
    st.session_state.mode = "Pattern Dashboard"

st.sidebar.header("Dashboard Mode")
mode = st.sidebar.radio(
    "Choose view",
    ["Pattern Dashboard", "1-Second Trading View"],
    index=0 if st.session_state.mode == "Pattern Dashboard" else 1
)
st.session_state.mode = mode

st.subheader("Controls")

col_run, col_stop, col_day, col_5day, col_month = st.columns(5)

with col_run:
    if st.button("▶ RUN LIVE", use_container_width=True):
        st.session_state.running = True
        if st.session_state.mode == "1-Second Trading View":
            st.session_state.view_period = "1d"
            st.session_state.interval = "1m"

with col_stop:
    if st.button("■ STOP", use_container_width=True):
        st.session_state.running = False

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

col_refresh, col_smooth, col_volume = st.columns(3)

with col_refresh:
    if st.session_state.mode == "1-Second Trading View":
        refresh_seconds = st.slider("Refresh speed", 1, 5, 1)
    else:
        refresh_seconds = st.slider("Refresh speed while live", 1, 10, 1)

with col_smooth:
    smooth_lines = st.checkbox("Smooth lines", value=True)

with col_volume:
    show_volume = st.checkbox("Show volume", value=True)

if st.session_state.running:
    st_autorefresh(interval=refresh_seconds * 1000, key="refresh")


@st.cache_data(ttl=1)
def load_data(period, interval):
    try:
        spy = yf.download("SPY", period=period, interval=interval, progress=False, auto_adjust=True)
        dia = yf.download("DIA", period=period, interval=interval, progress=False, auto_adjust=True)

        if spy.empty or dia.empty:
            return None, None

        return spy, dia

    except Exception as e:
        st.error(f"Data error: {e}")
        return None, None


def clean_close(df):
    close_series = df["Close"]

    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]

    close_series = pd.to_numeric(close_series, errors="coerce").dropna()
    return close_series


def clean_volume(df):
    volume_series = df["Volume"]

    if isinstance(volume_series, pd.DataFrame):
        volume_series = volume_series.iloc[:, 0]

    volume_series = pd.to_numeric(volume_series, errors="coerce").dropna()
    return volume_series


def get_prices(df):
    try:
        close_series = clean_close(df)

        if len(close_series) < 2:
            return None, None

        latest = float(close_series.iloc[-1])
        previous = float(close_series.iloc[-2])
        return latest, previous

    except Exception:
        return None, None


def make_single_chart(df, ticker, height=430):
    close = clean_close(df)
    chart_df = pd.DataFrame({"Close": close})

    if smooth_lines and len(chart_df) >= 5:
        chart_df["Close"] = chart_df["Close"].rolling(3, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_df.index,
        y=chart_df["Close"],
        mode="lines",
        name=ticker,
        line_shape="spline" if smooth_lines else "linear"
    ))

    fig.update_layout(
        height=height,
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10)
    )

    return fig


def make_joined_pattern_chart(spy_df, dia_df, height=520):
    spy_close = clean_close(spy_df)
    dia_close = clean_close(dia_df)

    joined = pd.concat(
        [spy_close.rename("SPY"), dia_close.rename("DIA")],
        axis=1
    ).dropna()

    if joined.empty or len(joined) < 2:
        return None, None

    normalized = joined.copy()
    normalized["SPY Pattern"] = (normalized["SPY"] / normalized["SPY"].iloc[0] - 1) * 100
    normalized["DIA Pattern"] = (normalized["DIA"] / normalized["DIA"].iloc[0] - 1) * 100

    if smooth_lines and len(normalized) >= 5:
        normalized["SPY Pattern"] = normalized["SPY Pattern"].rolling(3, min_periods=1).mean()
        normalized["DIA Pattern"] = normalized["DIA Pattern"].rolling(3, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized["SPY Pattern"],
        mode="lines",
        name="SPY Pattern",
        line_shape="spline" if smooth_lines else "linear"
    ))

    fig.add_trace(go.Scatter(
        x=normalized.index,
        y=normalized["DIA Pattern"],
        mode="lines",
        name="DIA Pattern",
        line_shape="spline" if smooth_lines else "linear"
    ))

    fig.add_hline(y=0, line_dash="dash")

    fig.update_layout(
        height=height,
        title="Joined Pattern Chart: SPY vs DIA",
        xaxis_title="Time",
        yaxis_title="Move From Start (%)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=10)
    )

    return fig, normalized


def show_metrics(spy, dia):
    spy_latest, spy_prev = get_prices(spy)
    dia_latest, dia_prev = get_prices(dia)

    if spy_latest is None or dia_latest is None:
        st.warning("Not enough market data yet.")
        st.stop()

    spy_change = spy_latest - spy_prev
    dia_change = dia_latest - dia_prev

    spy_open = float(clean_close(spy).iloc[0])
    dia_open = float(clean_close(dia).iloc[0])

    spy_open_move = spy_latest - spy_open
    dia_open_move = dia_latest - dia_open

    spy_open_pct = (spy_latest / spy_open - 1) * 100
    dia_open_pct = (dia_latest / dia_open - 1) * 100

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("SPY Last", f"${spy_latest:.2f}", f"{spy_change:.2f}")
    m2.metric("SPY From Open", f"{spy_open_pct:.2f}%", f"${spy_open_move:.2f}")
    m3.metric("DIA Last", f"${dia_latest:.2f}", f"{dia_change:.2f}")
    m4.metric("DIA From Open", f"{dia_open_pct:.2f}%", f"${dia_open_move:.2f}")

    return {
        "spy_latest": spy_latest,
        "dia_latest": dia_latest,
        "spy_change": spy_change,
        "dia_change": dia_change,
        "spy_open_move": spy_open_move,
        "dia_open_move": dia_open_move,
        "spy_open_pct": spy_open_pct,
        "dia_open_pct": dia_open_pct
    }


# Force 1-second mode to use intraday 1m source data, refreshed every second.
if st.session_state.mode == "1-Second Trading View":
    period = "1d"
    interval = "1m"
else:
    period = st.session_state.view_period
    interval = st.session_state.interval

spy, dia = load_data(period, interval)

if spy is None or dia is None:
    st.warning("Market data unavailable right now. Try again in a minute or switch the time view.")
    st.stop()

status = "LIVE RUNNING" if st.session_state.running else "PAUSED"
st.info(f"Status: {status} | Mode: {st.session_state.mode} | Source interval: {interval} | Screen refresh: {refresh_seconds}s")

metrics = show_metrics(spy, dia)

if st.session_state.mode == "1-Second Trading View":
    st.subheader("1-Second Trading View")
    st.caption("This screen refreshes every second when RUN LIVE is on. Yahoo/yfinance still supplies 1-minute bars, so the display updates every second but the source candles are not true tick data.")

    joined_fig, normalized = make_joined_pattern_chart(spy, dia, height=620)

    if joined_fig:
        st.plotly_chart(joined_fig, use_container_width=True)

        latest_spy_pattern = float(normalized["SPY Pattern"].iloc[-1])
        latest_dia_pattern = float(normalized["DIA Pattern"].iloc[-1])
        spread = latest_spy_pattern - latest_dia_pattern

        c1, c2, c3 = st.columns(3)
        c1.metric("SPY Pattern Move", f"{latest_spy_pattern:.2f}%")
        c2.metric("DIA Pattern Move", f"{latest_dia_pattern:.2f}%")
        c3.metric("SPY vs DIA Spread", f"{spread:.2f}%")

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_single_chart(spy, "SPY", height=360), use_container_width=True)
    with col2:
        st.plotly_chart(make_single_chart(dia, "DIA", height=360), use_container_width=True)

else:
    st.subheader("Pattern Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SPY Chart")
        st.plotly_chart(make_single_chart(spy, "SPY"), use_container_width=True)

    with col2:
        st.subheader("DIA Chart")
        st.plotly_chart(make_single_chart(dia, "DIA"), use_container_width=True)

    st.divider()
    st.subheader("Joined Pattern Reader")

    joined_fig, normalized = make_joined_pattern_chart(spy, dia)

    if joined_fig is None:
        st.warning("Could not build joined pattern chart yet.")
    else:
        st.plotly_chart(joined_fig, use_container_width=True)

        latest_spy_pattern = float(normalized["SPY Pattern"].iloc[-1])
        latest_dia_pattern = float(normalized["DIA Pattern"].iloc[-1])
        spread = latest_spy_pattern - latest_dia_pattern

        c1, c2, c3 = st.columns(3)
        c1.metric("SPY Pattern Move", f"{latest_spy_pattern:.2f}%")
        c2.metric("DIA Pattern Move", f"{latest_dia_pattern:.2f}%")
        c3.metric("SPY vs DIA Spread", f"{spread:.2f}%")

if show_volume:
    st.divider()
    st.subheader("Volume")

    spy_volume = clean_volume(spy)
    dia_volume = clean_volume(dia)

    volume_fig = go.Figure()

    volume_fig.add_trace(go.Bar(
        x=spy_volume.index,
        y=spy_volume,
        name="SPY Volume",
        opacity=0.65
    ))

    volume_fig.add_trace(go.Bar(
        x=dia_volume.index,
        y=dia_volume,
        name="DIA Volume",
        opacity=0.65
    ))

    volume_fig.update_layout(
        height=330,
        template="plotly_dark",
        barmode="overlay",
        xaxis_title="Time",
        yaxis_title="Volume",
        margin=dict(l=10, r=10, t=30, b=10)
    )

    st.plotly_chart(volume_fig, use_container_width=True)

st.divider()

snapshot = pd.DataFrame({
    "Ticker": ["SPY", "DIA"],
    "Last Price": [metrics["spy_latest"], metrics["dia_latest"]],
    "Last Bar Change": [metrics["spy_change"], metrics["dia_change"]],
    "Move From Open": [metrics["spy_open_move"], metrics["dia_open_move"]],
    "Move From Open %": [metrics["spy_open_pct"], metrics["dia_open_pct"]]
})

st.subheader("Market Snapshot")
st.dataframe(snapshot, use_container_width=True)

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
st.caption("No API key required. Data source: yfinance / Yahoo Finance. For true 1-second tick data, you would need a paid real-time market data feed.")
