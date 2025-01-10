# kline_fetcher.py
import threading
import time
from datetime import datetime, timedelta

import requests
from app_config import AppConfig
from loguru import logger

KLINE_LIMIT = 500
INTERVALS = ["1m", AppConfig.cover_kline_interval]


class KlineFetcher:
    def __init__(self, cryptos, intervals=INTERVALS):
        self.price_lock = threading.Lock()
        self.cryptos = cryptos
        self.intervals = intervals
        logger.info(f"Initialized with intervals: {self.intervals}")

    @staticmethod
    def fetch_symbol_historical_data(symbol, interval):
        """Fetch historical kline data for a given symbol and interval."""
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": interval,
            "limit": KLINE_LIMIT,
        }

        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return [
                [
                    int(k[0]),  # Open time
                    float(k[1]),  # Open price
                    float(k[2]),  # High price
                    float(k[3]),  # Low price
                    float(k[4]),  # Close price
                    float(k[5]),  # Volume
                    int(k[6]),  # Close time
                    float(k[7]),  # Quote asset volume
                    int(k[8]),  # Number of trades
                    float(k[9]),  # Taker buy base asset volume
                    float(k[10]),  # Taker buy quote asset volume
                ]
                for k in response.json()
            ]
        except requests.RequestException as e:
            logger.error(f"Failed to fetch klines for {symbol}: {e}")
            return None

    def save_historical_data_concurrently(self, cryptos = None):
        """
        Fetch historical data for all symbols and intervals concurrently.
        """
        if not cryptos:
            cryptos = self.cryptos.values()
        threads = []
        total_tasks = len(self.cryptos.values()) * len(self.intervals)
        completed_tasks = 0

        for crypto in cryptos:
            symbol = crypto.symbol
            for interval in self.intervals:
                thread = threading.Thread(
                    target=self._fetch_and_store_klines, args=(symbol, interval)
                )
                threads.append(thread)
                thread.start()

                # Update and display progress
                completed_tasks += 1
                AppConfig.show_progress(completed_tasks, total_tasks, symbol, interval)

        for thread in threads:
            thread.join()


    def _fetch_and_store_klines(self, symbol, interval):
        """
        Helper function to fetch and store klines for a single symbol and interval.
        """
        klines = self.fetch_symbol_historical_data(symbol, interval)
        if klines:
            if not interval == "1m":
                interval = "cover"

            self.cryptos[symbol].__setattr__(f"klines_{interval}", klines)

    def create_new_kline(self, last_kline, current_price):
        """Create a new kline based on the last kline and current price."""
        new_kline = list(last_kline)
        new_kline[0] = int(
            datetime.now().timestamp() * 1000
        )  # Set the open time to the current time
        new_kline[1] = new_kline[4]
        new_kline[2] = current_price
        new_kline[3] = current_price
        new_kline[4] = current_price
        new_kline[5] = 0
        new_kline[6] = int(
            datetime.now().timestamp() * 1000
        )  # Set the close time to the current time
        new_kline[7] = 0
        new_kline[8] = 0
        new_kline[9] = 0
        new_kline[10] = 0
        return new_kline

    def update_current_kline(self, kline, current_price):
        """Update the current kline with the latest price."""
        kline[2] = max(kline[2], current_price)  # Update high price
        kline[3] = min(kline[3], current_price)  # Update low price
        kline[4] = current_price  # Update close price
