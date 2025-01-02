import requests
import pandas as pd
import plotly.graph_objects as go

def fetch_kline_data(symbol, interval, limit=500):
    """Fetches kline data from the Binance API."""
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching kline data: {e}")
        return None

def create_candlestick_chart(df):
    """Creates a candlestick chart using Plotly."""
    if df is None or df.empty:
        print("No data to display.")
        return

    fig = go.Figure(data=[go.Candlestick(
        x=df['Date'],
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close']
    )])
    fig.update_layout(title="Candlestick Chart", yaxis_title="Price")

    # Try different methods to show the chart
    try:
        fig.show()
    except Exception as e:
        print(f"Error showing chart: {e}")
        try:
            fig.write_html("candlestick_chart.html")
            print("Chart saved as candlestick_chart.html")
        except Exception as e:
            print(f"Error saving chart: {e}")

if __name__ == "__main__":
    symbol = "BTCUSDT"
    interval = AppConfig.cover_kline
    kline_data = fetch_kline_data(symbol, interval)

    if kline_data is not None:
        df = pd.DataFrame(kline_data, columns=[
            "Open time", "Open", "High", "Low", "Close", "Volume", "Close time",
            "Quote asset volume", "Number of trades", "Taker buy base asset volume",
            "Taker buy quote asset volume", "Ignore"
        ])
        df['Date'] = pd.to_datetime(df['Open time'], unit='ms')
        df['Open'] = pd.to_numeric(df['Open'])
        df['High'] = pd.to_numeric(df['High'])
        df['Low'] = pd.to_numeric(df['Low'])
        df['Close'] = pd.to_numeric(df['Close'])
        create_candlestick_chart(df)
    else:
        print("Failed to fetch kline data.")