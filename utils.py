import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pandas as pd
import requests
from loguru import logger

BASE_URL = "https://api.binance.com"


def fetch_all_symbols(quote_asset="USDT", api_endpoint=BASE_URL):
    """Fetch all symbols from Binance with the specified quote asset."""
    try:
        response = requests.get(f"{api_endpoint}/api/v3/exchangeInfo")
        response.raise_for_status()
        data = response.json()
        
        symbols = [
            symbol["symbol"]
            for symbol in data["symbols"]
            if symbol["quoteAsset"] == quote_asset and symbol["status"] == "TRADING"
        ]
        
        if symbols:
            logger.debug(f"Fetched {len(symbols)} symbols with {quote_asset} as the quote asset.")
        else:
            logger.warning(f"No symbols found with {quote_asset} as the quote asset. Check rate limits or asset availability.")
        
        return symbols
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching symbols: {e}")
        return []



def find_outliers_zscore(data, threshold=2):
  """
  Identifies outliers in a dataset using the Z-score method.

  Args:
    data: A NumPy array of data values.
    threshold: The Z-score threshold beyond which a data point is 
               considered an outlier. Defaults to 2.

  Returns:
    A NumPy array containing the outlier values.
  """
  mean = np.mean(data)
  std = np.std(data)
  if std == 0:
    std = std + 1e-10
  z_scores = (data - mean) / std
  outliers = data[np.abs(z_scores) > threshold]
  return outliers


def generate_candlestick_chart(klines, timeframe):
    """
    Generates a candlestick chart using Plotly.

    Args:
      klines: A list of kline data.
      timeframe: The timeframe of the klines ('1m' or AppConfig.cover_kline).

    Returns:
      An HTML string containing the candlestick chart.
    """
    try:
        # Dynamically adjust column names based on klines data
        column_names = ['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume', 
                        'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume']
        if len(klines[0]) == 12:
            column_names.append('Ignore')  # Add 'Ignore' column if present

        df = pd.DataFrame(klines, columns=column_names)
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')  # Convert timestamps to datetime objects

        fig = go.Figure(data=[go.Candlestick(x=df['Open time'],
                        open=df['Open'],
                        high=df['High'],
                        low=df['Low'],
                        close=df['Close'])])

        fig.update_layout(title=f"{timeframe} Candlestick Chart",
                          xaxis_title="Time",
                          yaxis_title="Price")

        return fig.to_html(full_html=False, include_plotlyjs='cdn')  # Return the chart as an HTML string

    except Exception as e:
        logger.error(f"Error generating candlestick chart: {e}")
        return f"<p>Error generating candlestick chart for {timeframe} timeframe.</p>"

def round_up_to_nearest(x, base):
  """Rounds up a number to the nearest multiple of a given base.

  Args:
    x: The number to round up.
    base: The base to round up to.

  Returns:
    The rounded up number as a float.
  """
  return truncate_amount(float(np.ceil(x / base) * base), base)

def truncate_amount(amount, precision):
    """
    Truncate a given amount to the specified precision.
    
    Parameters:
        amount (float): The number to be truncated.
        precision (float): The precision to truncate to (e.g., 0.01 for 2 decimal places).
    
    Returns:
        str: The truncated amount as a string formatted to the specified precision.
    """
    # Calculate the number of decimal places from the precision
    decimal_places = abs(int(f"{precision:.1e}".split("e")[-1]))
    
    # Truncate the amount to the precision
    truncated_amount = round(amount / precision) * precision
    
    # Format the truncated amount using the calculated decimal places
    return f"{truncated_amount:.{decimal_places}f}"


def format_float(number_string):  # remove precision
    if "e-" in number_string:
        precision = int(number_string.split('e-')[1])  # Extract precision from the exponent
    else:  # precision is the number of digits after the decimal point
        precision = len(number_string.split('.')[1]) 
    return "{:.{precision}f}".format(float(number_string), precision=precision)  # Format the number