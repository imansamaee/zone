import asyncio
from functools import wraps
import threading
import time
from loguru import logger

from app_config import AppConfig
from async_price_updater import AsyncPriceUpdater
from kline_fetcher import KlineFetcher
from order_authorization import OrderAuthorization
from order_creator import OrderCreator
from order_manager import OrderManager
from products import Products




class UpdateBot:
    def __init__(self):
        self.bot = Bot()  # don't instantiate bot again

    async def start_updaters(self):
        """
        Start the price updater, order creator, and kline updater tasks.
        """
        logger.info("Starting updaters...")
        try:
            AppConfig.tasks.append(asyncio.create_task(self.bot.run_price_updater_async()))
            AppConfig.tasks.append(asyncio.create_task(self.bot.update_latest_data()))
            # Start order creator
            AppConfig.tasks.append(asyncio.create_task(self.bot.start_order_creator()))
            # Update bot info after starting updaters
        except Exception as e:
            logger.error(f"Error starting updaters: {e}")

class Bot:
    def __init__(self):
        """
        Initialize the bot components.
        """
        logger.info("Initializing bot components...")

        self.products = Products()
        asyncio.create_task(self.products.update_cryptos_klines())

        self.order_authorization = OrderAuthorization(
            crypto_data=self.products.cryptos, volatility_threshold=0.5
        )

        self.order_manager = OrderManager()
        self.order_creator = OrderCreator(
            order_manager=self.order_manager,
            order_authorization=self.order_authorization,
            products=self.products
        )

        self.price_updater = AsyncPriceUpdater(self.products.cryptos)

        logger.info("Bot initialization complete.")


    async def start_order_creator(self): # where this one is started?
        """
        Start the order creator task.
        """
        try:
            logger.info("Starting order creator...")
            await self.order_creator.check_and_create_orders()
        except Exception as e:
            logger.error(f"Error starting order creator: {e}")

    async def run_price_updater_async(self):
        """
        Run the price updater asynchronously.
        """
        logger.info("Starting run_price_updater_async")
        try:
            await self.price_updater.start()
        except Exception as e:
            logger.error(f"Error running price updater: {e}")

    async def update_latest_data(self):
        """
        Update the latest kline data periodically.
        """
        logger.info("Starting update_latest_data")
        await AppConfig.bot_ready.wait()
        while not AppConfig.is_shutdown_initiated:
            try:
                self.products.kline_fetcher.update_latest_klines()
                self.check_nominees()
            except Exception as e:
                logger.error(f"Error updating latest data: {e}")
            time.sleep(60)

    def check_nominees(self):
        """
        Check for crypto nominees.
        """
        try:
            nominees = self.order_authorization.get_nominees()
            if nominees:
                logger.info(f"Nominees: {', '.join(nominees)}")
            else:
                logger.info("No nominees found.")
        except Exception as e:
            logger.error(f"Error checking nominees: {e}")
            
def init_bot():
    if AppConfig.bot is None: 
        update_bot = UpdateBot()
        AppConfig.bot = update_bot.bot
        asyncio.create_task(update_bot.start_updaters())
    AppConfig.is_shutdown_initiated = False
    AppConfig.bot_info.bot_is_running = True    
            
            
