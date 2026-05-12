# S&P 500 + Dow Jones 1-Second Dashboard

A Streamlit dashboard that streams Polygon second aggregates for two instruments at once.

## Best symbols
- `SPY` = S&P 500 ETF proxy
- `DIA` = Dow Jones ETF proxy
- `I:SPX` and `I:DJI` may work if your Polygon plan includes index second aggregates.

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste your Polygon API key in the sidebar, or set it first:
```bash
set POLYGON_API_KEY=your_key_here
streamlit run app.py
```

On Mac/Linux:
```bash
export POLYGON_API_KEY=your_key_here
streamlit run app.py
```
