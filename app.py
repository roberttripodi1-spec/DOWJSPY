
from datetime import datetime, time
from zoneinfo import ZoneInfo

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="SPY vs DIA Day Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Session State
# -----------------------------
if "running" not in st.session_state:
    st.session_state.running = False

if "view_period" not in st.session_state:
    st.session_state.view_period = "1d"

if "interval" not in st.session_state:
    st.session_state.interval = "1m"

if "mode" not in st.session_state:
    st.session_state.mode = "1-Second Trading View"


# -----------------------------
# Time / Market Helpers
# -----------------------------
def eastern_now():
    return datetime.now(ZoneInfo("America/New_York"))


def eastern_time_string():
    return eastern_now().strftime("%I:%M:%S %p ET")


def market_status():
    now = eastern_now()
    weekday = now.weekday()
    current_time = now.time()

    if weekday >= 5:
        return "MARKET CLOSED", "Weekend"

    if time(4, 0) <= current_time < time(9, 30):
        return "PREMARKET", "4:00 AM - 9:30 AM ET"

    if time(9, 30) <= current_time < time(16, 0):
        return "MARKET OPEN", "9:30 AM - 4:00 PM ET"

    if time(16, 0) <= current_time < time(20, 0):
        return "AFTER HOURS", "4:00 PM - 8:00 PM ET"

    return "MARKET CLOSED", "Outside trading hours"


# -----------------------------
# Data Helpers
# -----------------------------
@st.cache_data(ttl=1)
def load_data(period, interval):
    try:
        spy = yf.download(
            "SPY",
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            prepost=True,
        )

        dia = yf.download(
            "DIA",
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            prepost=True,
        )

        if spy.empty or dia.empty:
            return None, None

        return spy, dia

    except Exception as e:
        st.error(f"Data error: {e}")
        return None, None


def flatten_if_needed(series_or_df):
    if isinstance(series_or_df, pd.DataFrame):
        return series_or_df.iloc[:, 0]
    return series_or_df


def clean_series(df, column):
    if column not in df.columns:
        return pd.Series(dtype=float)

    series = flatten_if_needed(df[column])
    return pd.to_numeric(series, errors="coerce").dropna()


def clean_close(df):
    return clean_series(df, "Close")


def clean_high(df):
    return clean_series(df, "High")


def clean_low(df):
    return clean_series(df, "Low")


def clean_volume(df):
    return clean_series(df, "Volume")


def get_prices(df):
    close_series = clean_close(df)

    if len(close_series) < 2:
        return None, None

    return float(close_series.iloc[-1]), float(close_series.iloc[-2])


def safe_open(close_series):
    if close_series.empty:
        return None
    return float(close_series.iloc[0])


def calc_vwap(df):
    close = clean_close(df)
    volume = clean_volume(df)

    joined = pd.concat([close.rename("Close"), volume.rename("Volume")], axis=1).dropna()

    if joined.empty or joined["Volume"].sum() == 0:
        return None

    return float((joined["Close"] * joined["Volume"]).sum() / joined["Volume"].sum())


def calc_trading_stats(df):
    close = clean_close(df)
    high = clean_high(df)
    low = clean_low(df)
    volume = clean_volume(df)

    if close.empty:
        return None

    latest = float(close.iloc[-1])
    previous = float(close.iloc[-2]) if len(close) >= 2 else latest
    open_price = float(close.iloc[0])
    high_price = float(high.max()) if not high.empty else float(close.max())
    low_price = float(low.min()) if not low.empty else float(close.min())
    vwap = calc_vwap(df)

    return {
        "latest": latest,
        "previous": previous,
        "bar_change": latest - previous,
        "open": open_price,
        "from_open": latest - open_price,
        "from_open_pct": ((latest / open_price) - 1) * 100 if open_price else 0,
        "high": high_price,
        "low": low_price,
        "range": high_price - low_price,
        "volume": int(volume.sum()) if not volume.empty else 0,
        "vwap": vwap,
        "above_vwap": latest > vwap if vwap else None,
    }


def style_direction(value):
    if value > 0:
        return "▲"
    if value < 0:
        return "▼"
    return "■"


# -----------------------------
# Chart Helpers
# -----------------------------
def add_reference_lines(fig, stats, show_vwap=True, show_open=True, show_high_low=True):
    if stats is None:
        return fig

    if show_open:
        fig.add_hline(
            y=stats["open"],
            line_dash="dot",
            annotation_text="Open",
            annotation_position="top left",
        )

    if show_vwap and stats["vwap"] is not None:
        fig.add_hline(
            y=stats["vwap"],
            line_dash="dash",
            annotation_text="VWAP approx",
            annotation_position="bottom left",
        )

    if show_high_low:
        fig.add_hline(
            y=stats["high"],
            line_dash="dot",
            annotation_text="High",
            annotation_position="top right",
        )
        fig.add_hline(
            y=stats["low"],
            line_dash="dot",
            annotation_text="Low",
            annotation_position="bottom right",
        )

    return fig


def make_single_chart(df, ticker, stats, height=430, smooth=True, show_refs=True):
    close = clean_close(df)
    chart_df = pd.DataFrame({"Close": close})

    if smooth and len(chart_df) >= 5:
        chart_df["Close"] = chart_df["Close"].rolling(3, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=chart_df.index,
            y=chart_df["Close"],
            mode="lines",
            name=ticker,
            line_shape="spline" if smooth else "linear",
        )
    )

    if show_refs:
        fig = add_reference_lines(fig, stats)

    fig.update_layout(
        height=height,
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=30, b=10),
    )

    return fig


def make_joined_pattern_chart(spy_df, dia_df, height=520, smooth=True, show_spread=True):
    spy_close = clean_close(spy_df)
    dia_close = clean_close(dia_df)

    joined = pd.concat(
        [spy_close.rename("SPY"), dia_close.rename("DIA")],
        axis=1,
    ).dropna()

    if joined.empty or len(joined) < 2:
        return None, None

    normalized = joined.copy()
    normalized["SPY Pattern"] = (normalized["SPY"] / normalized["SPY"].iloc[0] - 1) * 100
    normalized["DIA Pattern"] = (normalized["DIA"] / normalized["DIA"].iloc[0] - 1) * 100
    normalized["Spread"] = normalized["SPY Pattern"] - normalized["DIA Pattern"]

    if smooth and len(normalized) >= 5:
        normalized["SPY Pattern"] = normalized["SPY Pattern"].rolling(3, min_periods=1).mean()
        normalized["DIA Pattern"] = normalized["DIA Pattern"].rolling(3, min_periods=1).mean()
        normalized["Spread"] = normalized["Spread"].rolling(3, min_periods=1).mean()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=normalized.index,
            y=normalized["SPY Pattern"],
            mode="lines",
            name="SPY Pattern",
            line_shape="spline" if smooth else "linear",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=normalized.index,
            y=normalized["DIA Pattern"],
            mode="lines",
            name="DIA Pattern",
            line_shape="spline" if smooth else "linear",
        )
    )

    if show_spread:
        fig.add_trace(
            go.Scatter(
                x=normalized.index,
                y=normalized["Spread"],
                mode="lines",
                name="SPY-DIA Spread",
                line=dict(dash="dot"),
            )
        )

    fig.add_hline(y=0, line_dash="dash")

    fig.update_layout(
        height=height,
        title="Joined Pattern Chart: SPY vs DIA",
        xaxis_title="Time",
        yaxis_title="Move From Start (%)",
        template="plotly_dark",
        hovermode="x unified",
        margin=dict(l=10, r=10, t=50, b=10),
    )

    return fig, normalized


def make_volume_chart(spy, dia):
    spy_volume = clean_volume(spy)
    dia_volume = clean_volume(dia)

    volume_fig = go.Figure()

    volume_fig.add_trace(
        go.Bar(
            x=spy_volume.index,
            y=spy_volume,
            name="SPY Volume",
            opacity=0.65,
        )
    )

    volume_fig.add_trace(
        go.Bar(
            x=dia_volume.index,
            y=dia_volume,
            name="DIA Volume",
            opacity=0.65,
        )
    )

    volume_fig.update_layout(
        height=330,
        template="plotly_dark",
        barmode="overlay",
        xaxis_title="Time",
        yaxis_title="Volume",
        margin=dict(l=10, r=10, t=30, b=10),
    )

    return volume_fig


# -----------------------------
# Button Styling
# -----------------------------
run_color = "#00cc66" if st.session_state.running else "#444444"
stop_color = "#ff3333" if not st.session_state.running else "#444444"

st.markdown(
    f"""
    <style>
    div.stButton > button {{
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }}

    div[data-testid="column"]:nth-of-type(1) button {{
        background-color: {run_color};
        color: white;
        border: 1px solid {run_color};
    }}

    div[data-testid="column"]:nth-of-type(2) button {{
        background-color: {stop_color};
        color: white;
        border: 1px solid {stop_color};
    }}

    .small-note {{
        color: #AAAAAA;
        font-size: 0.9rem;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Header / Controls
# -----------------------------
st.title("SPY vs DIA Day Trading Dashboard")
st.caption("Optimized for quick intraday pattern reading while keeping the original dual-mode setup.")

st.sidebar.header("Dashboard Mode")
mode = st.sidebar.radio(
    "Choose view",
    ["1-Second Trading View", "Pattern Dashboard"],
    index=0 if st.session_state.mode == "1-Second Trading View" else 1,
)
st.session_state.mode = mode

st.sidebar.header("Display Settings")
smooth_lines = st.sidebar.checkbox("Smooth lines", value=True)
show_volume = st.sidebar.checkbox("Show volume", value=True)
show_reference_lines = st.sidebar.checkbox("Show open / high / low / VWAP lines", value=True)
show_spread_line = st.sidebar.checkbox("Show SPY-DIA spread line", value=True)

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

if st.session_state.mode == "1-Second Trading View":
    refresh_seconds = st.sidebar.slider("Screen refresh speed", 1, 5, 1)
else:
    refresh_seconds = st.sidebar.slider("Screen refresh speed", 1, 10, 1)

if st.session_state.running:
    st_autorefresh(interval=refresh_seconds * 1000, key="refresh")


# -----------------------------
# Data Mode
# -----------------------------
if st.session_state.mode == "1-Second Trading View":
    period = "1d"
    interval = "1m"
else:
    period = st.session_state.view_period
    interval = st.session_state.interval

spy, dia = load_data(period, interval)

if spy is None or dia is None:
    st.warning("Market data unavailable right now. Try again in a minute or switch the time view.")
    st.caption(f"Last checked: {eastern_time_string()}")
    st.stop()

spy_stats = calc_trading_stats(spy)
dia_stats = calc_trading_stats(dia)

if spy_stats is None or dia_stats is None:
    st.warning("Not enough market data yet.")
    st.caption(f"Last checked: {eastern_time_string()}")
    st.stop()

mkt_status, mkt_detail = market_status()
status = "LIVE RUNNING" if st.session_state.running else "PAUSED"

st.info(
    f"Status: {status} | {mkt_status} ({mkt_detail}) | Mode: {st.session_state.mode} | "
    f"Source interval: {interval} | Screen refresh: {refresh_seconds}s | Time: {eastern_time_string()}"
)


# -----------------------------
# Fast Trading Readout
# -----------------------------
spy_vwap_state = "Above VWAP" if spy_stats["above_vwap"] else "Below VWAP" if spy_stats["above_vwap"] is not None else "VWAP N/A"
dia_vwap_state = "Above VWAP" if dia_stats["above_vwap"] else "Below VWAP" if dia_stats["above_vwap"] is not None else "VWAP N/A"

m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("SPY Last", f"${spy_stats['latest']:.2f}", f"{style_direction(spy_stats['bar_change'])} {spy_stats['bar_change']:.2f}")
m2.metric("SPY From Open", f"{spy_stats['from_open_pct']:.2f}%", f"${spy_stats['from_open']:.2f}")
m3.metric("SPY VWAP", spy_vwap_state)

m4.metric("DIA Last", f"${dia_stats['latest']:.2f}", f"{style_direction(dia_stats['bar_change'])} {dia_stats['bar_change']:.2f}")
m5.metric("DIA From Open", f"{dia_stats['from_open_pct']:.2f}%", f"${dia_stats['from_open']:.2f}")
m6.metric("DIA VWAP", dia_vwap_state)

# Quick interpretation strip
bias_parts = []
if spy_stats["from_open_pct"] > 0 and dia_stats["from_open_pct"] > 0:
    bias_parts.append("Both green from open")
elif spy_stats["from_open_pct"] < 0 and dia_stats["from_open_pct"] < 0:
    bias_parts.append("Both red from open")
else:
    bias_parts.append("Mixed index tone")

if spy_stats["above_vwap"] and dia_stats["above_vwap"]:
    bias_parts.append("both above VWAP")
elif spy_stats["above_vwap"] is False and dia_stats["above_vwap"] is False:
    bias_parts.append("both below VWAP")
else:
    bias_parts.append("VWAP divergence")

st.markdown(f"**Quick read:** {'; '.join(bias_parts)}.")


# -----------------------------
# Main Views
# -----------------------------
if st.session_state.mode == "1-Second Trading View":
    st.subheader("1-Second Trading View")
    st.caption(
        "Screen refreshes every second when RUN LIVE is on. Yahoo/yfinance does not provide true tick data here; "
        "it normally supplies 1-minute bars, refreshed on your screen every second."
    )

    joined_fig, normalized = make_joined_pattern_chart(
        spy,
        dia,
        height=640,
        smooth=smooth_lines,
        show_spread=show_spread_line,
    )

    if joined_fig is not None:
        st.plotly_chart(joined_fig, use_container_width=True)

        latest_spy_pattern = float(normalized["SPY Pattern"].iloc[-1])
        latest_dia_pattern = float(normalized["DIA Pattern"].iloc[-1])
        spread = latest_spy_pattern - latest_dia_pattern

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SPY Pattern Move", f"{latest_spy_pattern:.2f}%")
        c2.metric("DIA Pattern Move", f"{latest_dia_pattern:.2f}%")
        c3.metric("SPY vs DIA Spread", f"{spread:.2f}%")
        c4.metric("Leader", "SPY" if spread > 0 else "DIA" if spread < 0 else "Even")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SPY Price Action")
        st.plotly_chart(
            make_single_chart(
                spy,
                "SPY",
                spy_stats,
                height=380,
                smooth=smooth_lines,
                show_refs=show_reference_lines,
            ),
            use_container_width=True,
        )

    with col2:
        st.subheader("DIA Price Action")
        st.plotly_chart(
            make_single_chart(
                dia,
                "DIA",
                dia_stats,
                height=380,
                smooth=smooth_lines,
                show_refs=show_reference_lines,
            ),
            use_container_width=True,
        )

else:
    st.subheader("Pattern Dashboard")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("SPY Chart")
        st.plotly_chart(
            make_single_chart(
                spy,
                "SPY",
                spy_stats,
                smooth=smooth_lines,
                show_refs=show_reference_lines,
            ),
            use_container_width=True,
        )

    with col2:
        st.subheader("DIA Chart")
        st.plotly_chart(
            make_single_chart(
                dia,
                "DIA",
                dia_stats,
                smooth=smooth_lines,
                show_refs=show_reference_lines,
            ),
            use_container_width=True,
        )

    st.divider()
    st.subheader("Joined Pattern Reader")

    joined_fig, normalized = make_joined_pattern_chart(
        spy,
        dia,
        smooth=smooth_lines,
        show_spread=show_spread_line,
    )

    if joined_fig is None:
        st.warning("Could not build joined pattern chart yet.")
    else:
        st.plotly_chart(joined_fig, use_container_width=True)

        latest_spy_pattern = float(normalized["SPY Pattern"].iloc[-1])
        latest_dia_pattern = float(normalized["DIA Pattern"].iloc[-1])
        spread = latest_spy_pattern - latest_dia_pattern

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("SPY Pattern Move", f"{latest_spy_pattern:.2f}%")
        c2.metric("DIA Pattern Move", f"{latest_dia_pattern:.2f}%")
        c3.metric("SPY vs DIA Spread", f"{spread:.2f}%")
        c4.metric("Leader", "SPY" if spread > 0 else "DIA" if spread < 0 else "Even")


# -----------------------------
# Volume + Snapshot
# -----------------------------
if show_volume:
    st.divider()
    st.subheader("Volume")
    st.plotly_chart(make_volume_chart(spy, dia), use_container_width=True)

st.divider()

snapshot = pd.DataFrame(
    {
        "Ticker": ["SPY", "DIA"],
        "Last Price": [spy_stats["latest"], dia_stats["latest"]],
        "Last Bar Change": [spy_stats["bar_change"], dia_stats["bar_change"]],
        "Move From Open": [spy_stats["from_open"], dia_stats["from_open"]],
        "Move From Open %": [spy_stats["from_open_pct"], dia_stats["from_open_pct"]],
        "High": [spy_stats["high"], dia_stats["high"]],
        "Low": [spy_stats["low"], dia_stats["low"]],
        "Range": [spy_stats["range"], dia_stats["range"]],
        "VWAP Approx": [spy_stats["vwap"], dia_stats["vwap"]],
        "Volume": [spy_stats["volume"], dia_stats["volume"]],
    }
)

st.subheader("Market Snapshot")
st.dataframe(snapshot, use_container_width=True)

st.caption(f"Last updated: {eastern_time_string()}")
st.caption(
    "No API key required. Data source: yfinance / Yahoo Finance. "
    "For true 1-second tick data, use a paid real-time feed such as Polygon, Alpaca, Tradier, or Interactive Brokers."
)
