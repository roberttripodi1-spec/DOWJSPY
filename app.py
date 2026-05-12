
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

st.set_page_config(
    page_title="SPY vs DIA Live Zoom Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Session state
# -----------------------------
if "metrics_live" not in st.session_state:
    st.session_state.metrics_live = True

if "view_period" not in st.session_state:
    st.session_state.view_period = "1d"

if "interval" not in st.session_state:
    st.session_state.interval = "1m"


# -----------------------------
# Time helpers
# -----------------------------
def eastern_now():
    return datetime.now(ZoneInfo("America/New_York"))


def eastern_time_string():
    return eastern_now().strftime("%I:%M:%S %p ET")


def market_status():
    now = eastern_now()

    if now.weekday() >= 5:
        return "MARKET CLOSED", "Weekend"

    t = now.time()

    if time(4, 0) <= t < time(9, 30):
        return "PREMARKET", "4:00 AM - 9:30 AM ET"

    if time(9, 30) <= t < time(16, 0):
        return "MARKET OPEN", "9:30 AM - 4:00 PM ET"

    if time(16, 0) <= t < time(20, 0):
        return "AFTER HOURS", "4:00 PM - 8:00 PM ET"

    return "MARKET CLOSED", "Outside trading hours"


# -----------------------------
# Data helpers
# -----------------------------
def convert_to_et_index(df):
    if df is None or df.empty:
        return df

    out = df.copy()

    try:
        if out.index.tz is None:
            out.index = out.index.tz_localize("UTC")
        out.index = out.index.tz_convert("America/New_York")
    except Exception:
        pass

    return out


@st.cache_data(ttl=15)
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

        return convert_to_et_index(spy), convert_to_et_index(dia)

    except Exception as e:
        st.error(f"Data error: {e}")
        return None, None


def flatten_col(x):
    if isinstance(x, pd.DataFrame):
        return x.iloc[:, 0]
    return x


def clean_series(df, col):
    if col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(flatten_col(df[col]), errors="coerce").dropna()


def clean_close(df):
    return clean_series(df, "Close")


def clean_high(df):
    return clean_series(df, "High")


def clean_low(df):
    return clean_series(df, "Low")


def clean_volume(df):
    return clean_series(df, "Volume")


def calc_vwap(df):
    close = clean_close(df)
    volume = clean_volume(df)

    joined = pd.concat([close.rename("Close"), volume.rename("Volume")], axis=1).dropna()

    if joined.empty or joined["Volume"].sum() == 0:
        return None

    return float((joined["Close"] * joined["Volume"]).sum() / joined["Volume"].sum())


def calc_stats(df):
    close = clean_close(df)
    high = clean_high(df)
    low = clean_low(df)
    volume = clean_volume(df)

    if close.empty or len(close) < 2:
        return None

    latest = float(close.iloc[-1])
    previous = float(close.iloc[-2])
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


def direction_icon(value):
    if value > 0:
        return "▲"
    if value < 0:
        return "▼"
    return "■"


def tradingview_widget():
    # This TradingView widget handles live updates and zoom/pan inside the chart itself.
    # Because the chart is not recreated every second by Streamlit, zoom does not snap back.
    html = """
    <div class="tradingview-widget-container" style="height:820px;width:100%;">
      <div id="tradingview_live_spy_dia" style="height:100%;width:100%;"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget({
        "autosize": true,
        "symbol": "AMEX:SPY",
        "interval": "1",
        "timezone": "America/New_York",
        "theme": "dark",
        "style": "2",
        "locale": "en",
        "enable_publishing": false,
        "hide_side_toolbar": false,
        "allow_symbol_change": true,
        "calendar": false,
        "details": true,
        "hotlist": false,
        "studies": [
          "Volume@tv-basicstudies",
          "VWAP@tv-basicstudies"
        ],
        "compareSymbols": [
          {
            "symbol": "AMEX:DIA",
            "position": "SameScale"
          }
        ],
        "container_id": "tradingview_live_spy_dia"
      });
      </script>
    </div>
    """
    components.html(html, height=850)


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    div.stButton > button {
        border-radius: 10px;
        height: 3em;
        font-weight: bold;
    }

    [data-testid="stMetric"] {
        background-color: rgba(255,255,255,0.035);
        border: 1px solid rgba(255,255,255,0.08);
        padding: 10px;
        border-radius: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# UI
# -----------------------------
st.title("SPY vs DIA Live Zoom Dashboard")
st.caption("Live chart updates while still letting you zoom, pan, and read the move without snap-back.")

st.sidebar.header("Live Chart")
st.sidebar.info(
    "The top chart uses a TradingView embedded chart. It updates live and lets you zoom/pan without Streamlit resetting your view."
)

st.sidebar.header("Metrics")
metrics_live = st.sidebar.checkbox("Auto-refresh metrics", value=st.session_state.metrics_live)
st.session_state.metrics_live = metrics_live

metric_refresh_seconds = st.sidebar.slider("Metrics refresh seconds", 15, 120, 30)

if metrics_live:
    st_autorefresh(interval=metric_refresh_seconds * 1000, key="metrics_refresh")

st.sidebar.header("Yahoo Metrics Timeframe")
period_choice = st.sidebar.selectbox(
    "Metrics timeframe",
    ["1d", "5d", "1mo"],
    index=["1d", "5d", "1mo"].index(st.session_state.view_period)
)

if period_choice == "1d":
    st.session_state.view_period = "1d"
    st.session_state.interval = "1m"
elif period_choice == "5d":
    st.session_state.view_period = "5d"
    st.session_state.interval = "5m"
else:
    st.session_state.view_period = "1mo"
    st.session_state.interval = "15m"

mkt_status, mkt_detail = market_status()

st.info(
    f"{mkt_status} ({mkt_detail}) | Chart timezone: Eastern Time | Last page update: {eastern_time_string()}"
)

st.subheader("Live SPY + DIA Chart")
st.caption(
    "Mouse wheel zoom and drag/pan are handled inside the live chart. "
    "DIA is overlaid as a comparison line on SPY."
)

tradingview_widget()

st.divider()
st.subheader("Dashboard Readout")

spy, dia = load_data(st.session_state.view_period, st.session_state.interval)

if spy is None or dia is None:
    st.warning("Yahoo metric data unavailable right now. The live chart above may still work.")
    st.stop()

spy_stats = calc_stats(spy)
dia_stats = calc_stats(dia)

if spy_stats is None or dia_stats is None:
    st.warning("Not enough metric data available yet.")
    st.stop()

spy_vwap_state = "Above VWAP" if spy_stats["above_vwap"] else "Below VWAP" if spy_stats["above_vwap"] is not None else "VWAP N/A"
dia_vwap_state = "Above VWAP" if dia_stats["above_vwap"] else "Below VWAP" if dia_stats["above_vwap"] is not None else "VWAP N/A"

m1, m2, m3, m4, m5, m6 = st.columns(6)

m1.metric("SPY Last", f"${spy_stats['latest']:.2f}", f"{direction_icon(spy_stats['bar_change'])} {spy_stats['bar_change']:.2f}")
m2.metric("SPY From Open", f"{spy_stats['from_open_pct']:.2f}%", f"${spy_stats['from_open']:.2f}")
m3.metric("SPY VWAP", spy_vwap_state)

m4.metric("DIA Last", f"${dia_stats['latest']:.2f}", f"{direction_icon(dia_stats['bar_change'])} {dia_stats['bar_change']:.2f}")
m5.metric("DIA From Open", f"{dia_stats['from_open_pct']:.2f}%", f"${dia_stats['from_open']:.2f}")
m6.metric("DIA VWAP", dia_vwap_state)

bias = []

if spy_stats["from_open_pct"] > 0 and dia_stats["from_open_pct"] > 0:
    bias.append("Both green from open")
elif spy_stats["from_open_pct"] < 0 and dia_stats["from_open_pct"] < 0:
    bias.append("Both red from open")
else:
    bias.append("Mixed index tone")

if spy_stats["above_vwap"] and dia_stats["above_vwap"]:
    bias.append("both above VWAP")
elif spy_stats["above_vwap"] is False and dia_stats["above_vwap"] is False:
    bias.append("both below VWAP")
else:
    bias.append("VWAP divergence")

spy_lead = spy_stats["from_open_pct"] - dia_stats["from_open_pct"]

st.markdown(f"**Quick read:** {'; '.join(bias)}.")
st.metric("SPY vs DIA Relative Lead", f"{spy_lead:.2f}%", "SPY leading" if spy_lead > 0 else "DIA leading" if spy_lead < 0 else "Even")

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

st.caption(
    "Top chart: TradingView embedded live chart. Metrics: yfinance/Yahoo Finance, refreshed separately. "
    "This setup avoids the zoom snap-back caused by full-page Streamlit chart redraws."
)
