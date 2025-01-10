import asyncio
from collections import defaultdict
import gc

import ccxt
import requests
from loguru import logger

from app_config import AppConfig, TradingStrategy
from async_price_updater import AsyncPriceUpdater
from models.crypto import Crypto
from crypto_tag import CryptoTag
from kline_fetcher import KlineFetcher


class Products:
    def __init__(self):
        self.markets = self.fetch_markets()  # Fetch market data once
        self.symbols_data = self.fetch_symbols_data()[: AppConfig.CRYPTO_LIMIT]
        self.cryptos = self.initialize_cryptos()
        self.working_cryptos = None
        self.kline_fetcher = KlineFetcher(self.cryptos)
        self.crypto_tags = self.initialize_crypto_tags()
        self.price_updater = AsyncPriceUpdater(self.cryptos, interval=2)
        self.klines_initialized = False
        logger.info(
            f"Initialized Products with {len(self.cryptos)} cryptos and {len(self.crypto_tags)} tags."
        )
        self.tradable_cryptos = []

    def get_market_info(self, symbol_id):
        """
        Retrieves market info for the given symbol from fetched markets data.
        """
        for market in self.markets:
            if market["id"] == symbol_id:
                return market
        return None

    def fetch_markets(self):
        """
        Fetches market data from the exchange.
        """
        try:
            exchange = ccxt.binance(
                {
                    "apiKey": AppConfig.API_KEY,
                    "secret": AppConfig.API_SECRET,
                    "enableRateLimit": True,
                }
            )
            return exchange.fetch_markets()
        except Exception as e:
            logger.error(f"Error fetching markets: {e}")
            return []

    def initialize_cryptos(self):
        """
        Initialize Crypto objects with relevant data from the Binance API response
        and assign market info.
        """
        cryptos = {}
        for product in self.symbols_data:
            try:
                opening_price = float(product.get("o", "0"))
                current_price = float(product.get("c", "0"))
                if "stablecoin" in product.get("tags", []):
                    logger.debug(f"Skipping stablecoin: {product['s']}")
                    continue

                symbol = product["s"]
                market_info = self.get_market_info(symbol)
                price_filter = next(
                    (
                        f
                        for f in market_info["info"]["filters"]
                        if f["filterType"] == "PERCENT_PRICE_BY_SIDE"
                    ),
                    None,
                )
                price_precision = market_info["precision"][
                    "price"
                ]  # Extract price precision
                limits = market_info["limits"]

                cryptos[symbol] = Crypto(
                    symbol=symbol,
                    status=product.get("st", ""),
                    base_asset=product.get("b", ""),
                    quote_asset=product.get("q", ""),
                    base_asset_unit=product.get("ba", ""),  # Added base_asset_unit
                    quote_asset_unit=product.get("qa", ""),  # Added quote_asset_unit
                    minimum_quantity=product.get(
                        "minQty", 0.0
                    ),  # Added minimum_quantity
                    tick_size=product.get("tickSz", 0.0),  # Added tick_size
                    opening_price=opening_price,
                    current_price=current_price,
                    pair_market_type=product.get("pmt", ""),  # Added pair_market_type
                    pair_market_name=product.get("pmn", ""),  # Added pair_market_name
                    circulating_supply=product.get(
                        "cs", None
                    ),  # Added circulating_supply
                    tags=product.get("tags", []),
                    price_filter=price_filter,
                    price_precision=price_precision,
                    limits=limits,
                )
                logger.debug(
                    f"Initialized {product['s']} | Opening Price: {opening_price}, Current Price: {current_price}"
                )
            except Exception as e:
                logger.error(f"Error initializing crypto {product.get('s')}: {e}")
        return cryptos

    def get_working_cryptos(self):
        """
        Retrieves a dictionary of symbols for cryptos that meet the condition of 
        having a supply zone before an immediate demand zone.

        Returns:
            dict: A dictionary where the keys are crypto symbols, and the values are Crypto objects.
        """
        try:
            # Filter cryptos based on the condition
            working_cryptos = {
                symbol: crypto
                for symbol, crypto in self.cryptos.items()
                if crypto.zones.get('supply_zone_before_immediate_demand_zone', False)
            }

            # Logging the results
            logger.info(
                f"Identified {len(working_cryptos)} working cryptos: {list(working_cryptos.keys())}"
            )

            return working_cryptos  # Return the dictionary of working cryptos
        except Exception as e:
            logger.error(f"Error retrieving working cryptos: {e}")
            return {}  # Return an empty dictionary in case of an error



    def get_market_info(self, symbol):
        """
        Retrieves market info for the given symbol from fetched markets data.
        """
        for market in self.markets:
            if market["id"] == symbol:
                return market
        return None

    def initialize_crypto_tags(self):
        """
        Initialize CryptoTag objects for each unique tag.
        """
        crypto_tags = defaultdict(lambda: CryptoTag(tag=""))
        for crypto in self.cryptos.values():
            for tag in crypto.tags:
                crypto_tags[tag].tag = tag
                crypto_tags[tag].add_crypto(crypto)
        return list(crypto_tags.values())

    def fetch_symbols_data(self):
        try:
            data = AppConfig.binance_client.get_products()
            return [
                product
                for product in data.get("data", [])
                if product.get("q") == "USDT" and product.get("st") == "TRADING"
            ]
        except requests.RequestException as e:
            logger.error(f"Error fetching symbols: {e}")
            return []

    async def update_cryptos_klines(self):
        """
        Update the Klines for all cryptos every 30 minutes by default,
        or for the top 10 working cryptos every 10 seconds if the strategy is LRP.
        """
        await self.update_all_klines()
        self.working_cryptos = self.get_working_cryptos()
        
        while not AppConfig().is_shutdown_initiated:  # Ensure the loop stops on shutdown
            try:
                if AppConfig.trading_strategy == TradingStrategy.LRP:
                    # Short interval for LRP strategy
                    await asyncio.sleep(10)
                    logger.info("Updating Klines for working cryptos under LRP strategy...")
                    await self.update_all_klines("working")


                else:
                    await asyncio.sleep(AppConfig.updating_klines_interval)
                    logger.info("Updating Klines for all cryptos...")
                    await self.update_all_klines()

                logger.info("Klines update cycle complete.")
            except Exception as e:
                logger.error(f"Error updating Klines: {e}")

            if AppConfig.trading_strategy == TradingStrategy.FLASH:
                AppConfig.bot.order_manager.convert_all_assets_to_quote_currency()

    async def update_all_klines(self, cryptos = "all"):
        if cryptos == "all":
            self.kline_fetcher.cryptos = self.cryptos
        elif cryptos == "working":
            self.kline_fetcher.cryptos = self.working_cryptos 

        self.kline_fetcher.save_historical_data_concurrently()
        if cryptos == "all":
            self.cryptos = self.kline_fetcher.cryptos
        elif cryptos == "working":
            self.working_cryptos = self.kline_fetcher.cryptos

        self.klines_initialized = True

        for symbol, crypto in self.cryptos.items():
            try:
               # Assuming klines_cover is a list of klines, each kline being a list itself
                last_cover_kline = crypto.klines_cover[-1]
                last_volume = last_cover_kline[5]  # Assuming volume is the 6th element in a kline
                crypto.last_volume = last_volume * crypto.current_price
            except (IndexError, KeyError) as e:
                logger.error(f"Error updating last_volume for {symbol}: {e}")


    async def start_price_updater(self):
        try:
            logger.info("Starting price updater...")
            await self.price_updater.start()
        except Exception as e:
            logger.error(f"Error starting price updater: {e}")

    def stop_price_updater(self):
        try:
            logger.info("Stopping price updater...")
            self.price_updater.stop()
        except Exception as e:
            logger.error(f"Error stopping price updater: {e}")
