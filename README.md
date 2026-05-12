# SPY vs DIA Day Trading Optimized Dashboard

Keeps prior features:
- Pattern Dashboard
- 1-Second Trading View
- RUN LIVE button
- STOP button
- RUN turns green when active
- STOP turns red when paused
- TODAY / 5 DAY / 1 MONTH buttons
- Joined SPY vs DIA normalized pattern chart
- Individual SPY and DIA charts
- Volume chart
- 12-hour ET time display
- No API key required

Optimizations added:
- Market status: premarket, open, after hours, closed
- Fast trading readout
- Approx VWAP status
- Open / high / low / VWAP reference lines
- SPY-DIA spread line
- Leader readout
- Better sidebar controls
- Pre/post-market data enabled through yfinance
- More complete market snapshot

Important:
This app refreshes the screen every second, but yfinance/Yahoo generally provides 1-minute bars.
For true 1-second/tick data, connect a paid real-time feed.

## Run locally

pip install -r requirements.txt

streamlit run app.py

## Deploy

Upload app.py, requirements.txt, and README.md to GitHub.
Deploy through Streamlit Community Cloud.