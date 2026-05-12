
from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st

# Example EST/EDT formatted timestamp
est_now = datetime.now(ZoneInfo("America/New_York"))

formatted_time = est_now.strftime("%I:%M:%S %p EST")

st.title("SPY vs DIA Dashboard")
st.write(f"Last updated: {formatted_time}")
