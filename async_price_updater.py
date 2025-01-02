import asyncio
from datetime import datetime, timedelta

import numpy as np
import requests
from app_config import AppConfig
from loguru import logger

from utils import find_outliers_zscore


class AsyncPriceUpdater:
    def __init__(self, cryptos, interval=AppConfig.price_updater_interval):
        """
        :param cryptos: A dictionary of Crypto instances (keyed by symbol).
        :param interval: Update interval in seconds.
        """
        self.cryptos = cryptos
        self.interval = interval
        self.api_url = "https://api.binance.com/api/v3/ticker/price"
        self.stop_event = asyncio.Event()

    async def fetch_latest_prices(self):
        """Fetch the latest prices from Binance API."""
        try:
            response = requests.get(self.api_url)
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Fetched latest prices for {len(data)} symbols.")
            return {item["symbol"]: float(item["price"]) for item in data}
        except requests.RequestException as e:
            logger.error(f"Error fetching latest prices: {e}")
            return {}

    async def update_prices(self):
        """
        Continuously fetch and update the prices of all cryptos.
        """
        logger.debug("Starting update_prices loop.")
        while not AppConfig.is_shutdown_initiated:
            try:
                latest_prices = await self.fetch_latest_prices()

                for symbol, price in latest_prices.items():
                    if symbol in AppConfig.bot.products.cryptos:
                        crypto = AppConfig.bot.products.cryptos[symbol]

                        # Update the klines with the current price
                        self.update_klines_with_price_and_time(symbol, price)

                        crypto.current_price = price
                        logger.debug(f"Updated price for {symbol}: {price}")
                        
                await self.check_unusual_volatility()

            except Exception as e:
                logger.error(f"Error in update_prices: {e}")
            await asyncio.sleep(self.interval)
        logger.info("Exiting update_prices loop.")

    async def check_unusual_volatility(self):
        """
        Check for unusual volatility across all cryptos and update the
        is_unusual_volatility flag.
        """
        try:
            volatility_1m_array = np.array(
                [
                    crypto.volatility_factor_1m
                    for crypto in AppConfig.bot.products.cryptos.values()
                ]
            )
            volatility_cover_array = np.array(
                [
                    crypto.volatility_factor_cover
                    for crypto in AppConfig.bot.products.cryptos.values()
                ]
            )

            unusual_volatility_1m = find_outliers_zscore(
                volatility_1m_array
            )  # Or find_outliers_iqr
            unusual_volatility_cover = find_outliers_zscore(
                volatility_cover_array
            )  # Or find_outliers_iqr

            for crypto in AppConfig.bot.products.cryptos.values():
                if (
                    np.any(unusual_volatility_1m == crypto.volatility_factor_1m)  # Use np.any()
                    or np.any(unusual_volatility_cover == crypto.volatility_factor_cover) # Use np.any()
                ):
                    crypto.is_unusual_volatility = True
                else:
                    crypto.is_unusual_volatility = False

        except Exception as e:
            logger.error(f"Error checking unusual volatility: {e}")

    def update_klines_with_current_price(self, crypto, current_price):
        """
        Update the latest kline for the given crypto with the current price.
        Create a new kline if the current time is more than the kline interval.
        Use the last kline's time plus the interval for the new kline's open time.
        """
        try:
            now = datetime.now()
            current_time = int(now.timestamp() * 1000)

            # Update cover kline
            if crypto.klines_cover:
                latest_kline_cover = crypto.klines_cover[-1]
                if now - datetime.fromtimestamp(latest_kline_cover[0] / 1000) >= timedelta(
                    hours=1
                ):
                    # Create a new cover kline with open time = last kline's open time + 1 hour
                    new_kline_time = (
                        latest_kline_cover[0] + timedelta(hours=1).total_seconds() * 1000
                    )
                    new_kline = self.create_new_kline(latest_kline_cover, current_price)
                    new_kline[0] = int(new_kline_time)  # Set the open time
                    crypto.klines_cover.append(new_kline)
                    crypto.klines_cover = crypto.klines_cover[
                        -AppConfig.KLINE_LIMIT :
                    ]  # Trim the list
                    latest_kline_cover = crypto.klines_cover[-1]  # Update the reference
                latest_kline_cover[2] = max(latest_kline_cover[2], current_price)
                latest_kline_cover[3] = min(latest_kline_cover[3], current_price)
                latest_kline_cover[4] = current_price
                latest_kline_cover[6] = current_time

            # Update 1m kline
            if crypto.klines_1m:
                latest_kline_1m = crypto.klines_1m[-1]
                if now - datetime.fromtimestamp(latest_kline_1m[0] / 1000) >= timedelta(
                    minutes=1
                ):
                    # Create a new 1m kline with open time = last kline's open time + 1 minute
                    new_kline_time = (
                        latest_kline_1m[0] + timedelta(minutes=1).total_seconds() * 1000
                    )
                    new_kline = self.create_new_kline(latest_kline_1m, current_price)
                    new_kline[0] = int(new_kline_time)  # Set the open time
                    crypto.klines_1m.append(new_kline)
                    crypto.klines_1m = crypto.klines_1m[
                        -AppConfig.KLINE_LIMIT :
                    ]  # Trim the list
                    latest_kline_1m = crypto.klines_1m[-1]  # Update the reference
                latest_kline_1m[2] = max(latest_kline_1m[2], current_price)
                latest_kline_1m[3] = min(latest_kline_1m[3], current_price)
                latest_kline_1m[4] = current_price
                latest_kline_1m[6] = current_time

        except Exception as e:
            logger.error(f"Error updating klines for {crypto.symbol}: {e}")

    def update_klines_with_price_and_time(self, symbol, price):
        """
        Update the latest cover and 1m klines for the given symbol with the given price.
        """
        try:
            if symbol in AppConfig.bot.products.cryptos:
                crypto = AppConfig.bot.products.cryptos[symbol]
                self.update_klines_with_current_price(crypto, price)
        except Exception as e:
            logger.error(f"Error updating klines for {symbol}: {e}")

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

    async def start(self):
        """Start the price updater asynchronously."""
        logger.info("AsyncPriceUpdater started.")
        await self.update_prices()

    def stop(self):
        """Stop the price updater."""
        self.stop_event.set()
        logger.debug("AsyncPriceUpdater stopped.")
