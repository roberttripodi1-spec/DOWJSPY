# SPY vs DIA Dual Mode Dashboard

Includes two modes:

1. Pattern Dashboard
- TODAY / 5 DAY / 1 MONTH buttons
- Joined normalized SPY vs DIA pattern chart
- Volume chart
- Move-from-open metrics

2. 1-Second Trading View
- RUN LIVE / STOP buttons
- Screen refresh every 1 second
- Joined SPY vs DIA pattern chart at the top
- Individual SPY and DIA charts below

Important:
This version does not require an API key. It uses yfinance/Yahoo Finance.
The screen can refresh every second, but the source market bars are usually 1-minute bars.
For true tick-by-tick or 1-second bars, use a paid feed such as Polygon, Alpaca, Tradier, or Interactive Brokers.

## Run locally

pip install -r requirements.txt

streamlit run app.py

## Deploy

Upload app.py, requirements.txt, and README.md to GitHub.
Deploy the repo through Streamlit Community Cloud.