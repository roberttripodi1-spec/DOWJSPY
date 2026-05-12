# SPY vs DIA Live Zoom Dashboard

This version solves the zoom/reset problem by using a TradingView embedded chart for the live chart.

What changed:
- The top live chart updates on its own
- You can zoom and pan without Streamlit snapping the chart back
- DIA is overlaid on SPY as a comparison symbol
- Chart timezone is Eastern Time
- VWAP and Volume studies are included
- Metrics below still use yfinance/Yahoo Finance
- Metrics can auto-refresh separately every 15-120 seconds

Why this works:
Earlier versions used Streamlit to rerun the full page every few seconds. That redrew the Plotly chart and reset your zoom.
This version keeps the live chart inside the browser so zoom stays usable.

Run locally:

pip install -r requirements.txt

streamlit run app.py

Deploy:
Upload app.py, requirements.txt, and README.md to GitHub, then deploy through Streamlit Cloud.