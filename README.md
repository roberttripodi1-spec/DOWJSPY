# SPY vs DIA Stable Zoom Dashboard

Fixes:
- Reduced twitching from aggressive 1-second full-page reruns
- Default refresh is now 5 seconds
- User can choose 3-30 second refresh
- Mouse-wheel zoom stays enabled
- Plotly uirevision helps preserve zoom/pan
- Added manual REFRESH button
- Added Auto-follow latest bars toggle
- Added default visible window setting
- Charts show Eastern Time in 12-hour AM/PM format

Kept:
- RUN LIVE / STOP buttons
- RUN green when active
- STOP red when paused
- 1-Second Trading View
- Pattern Dashboard
- TODAY / 5 DAY / 1 MONTH
- Joined SPY/DIA pattern chart
- Volume
- VWAP/open/high/low lines

## Run locally

pip install -r requirements.txt

streamlit run app.py

## Deploy

Upload app.py, requirements.txt, and README.md to GitHub and deploy through Streamlit Cloud.