import asyncio
import os
import platform
import sys
import subprocess
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timezone
from binance.client import Client
from dotenv import load_dotenv
from enum import Enum
import time

from models.bot_info import BotInfo

load_dotenv()  # Load environment variables from .env

class TradingStrategy(Enum):
    """Enum representing different trading strategies."""
    TEST = "Testing Bot Performance"
    SUPPORT_RESISTANCE = "Support/Resistance Trading"
    SR_BREAKOUT = "S/R Breakout Trading"
    RANGE_BOUND = "Range-Bound Trading"
    ZONE = "Zone Trading"
    SRB = "SRB (Support Resistance Breakout)"
    BOUNCE = "Bounce Trading"
    CHANNEL_SURFER = "Channel Surfer"
    WALL_STREET_SHUFFLE = "The Wall Street Shuffle"
    FLASH = "Fast and Reckless"
    SUSPEND = "Halt trading activities"

class AppConfig:
    trading_strategy: TradingStrategy = TradingStrategy.SUSPEND

    run_bot: bool = True
    convert_assets: bool = False

    flash_pct: float = 0.1

    bot = None  # Replace Any with the actual type of your bot object
    is_shutdown_initiated: bool = False
    cover_kline_interval = "15m"
    volatility_factor: float = 2.0
    stability_factor: float = 1.0
    KLINE_LIMIT: int = 200
    CRYPTO_LIMIT: Optional[int] = None# 20 if trading_strategy == TradingStrategy.TEST or trading_strategy == TradingStrategy.SUSPEND else None
    init_pairs_history :bool = False if trading_strategy == TradingStrategy.TEST or trading_strategy == TradingStrategy.SUSPEND else True
    port: int = 8001
    ORDER_USDT_AMOUNT: int = 10
    MAX_USDT_TO_PLACE: int = 15
    API_KEY: str = os.environ.get("BINANCE_KEY")
    API_SECRET: str = os.environ.get("BINANCE_SECRET")
    binance_client: Client = Client(API_KEY, API_SECRET)
    bot_ready: asyncio.Event = asyncio.Event()
    tasks = [] 
    volatility: Dict[str, float] = {"one_m_low": 2, "one_m_high": 10, "one_h_low": 5, "one_h_high": 60}
    min_sr_gap_pct: int = 1
    support_closeness_threshold_pct: float = 0.5
    resistance_closeness_threshold_pct: float = 0.5
    check_buy_order_wait: int = 30
    check_sell_order_wait: int = 30
    price_updater_interval: int = 1
    check_and_create_orders_interval: int = 60
    monitor_orders_interval: int = 5
    updating_klines_interval: int = 30 * 60 if trading_strategy != TradingStrategy.FLASH else 60 * 60
    stop_loss_pct: float = 1.0
    binance_cost_pct: float = 0.1
    blacklist: List[str] = ['OMUSDT']
    
    
    bot_info = BotInfo()

    

    @staticmethod
    def get_config_as_dict():
        config_dict = {}
        for key, value in AppConfig.__dict__.items():  # Access class attributes directly
            if not key.startswith("_") and not callable(value):
                config_dict[key] = value
        return config_dict

        
    @staticmethod
    def rename_pairs_history_folder():
        if not AppConfig.init_pairs_history:
            return

        current_time = time.strftime("%Y-%m-%d-%H:%M:%S")

        # Construct the old and new folder names
        old_folder = "static/pairs_history"
        new_folder = f"static/pairs_history+{current_time}"
        if os.path.exists(old_folder) and os.path.isdir(old_folder):
            os.rename(old_folder, new_folder)

    @staticmethod
    def set_logger(log_level="INFO"):
        logger.remove()
        log_format = "<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        logger.add("main.log", format=log_format, level=log_level, rotation="1 MB")
        logger.add(sys.stdout, format=log_format, level=log_level) 

    @staticmethod
    def format_event_time(event_time):
        """Format the event_time as MM:SS, or return '00:00' if invalid."""
        try:
            # Check if the event_time is within a reasonable range, assuming milliseconds if large
            if event_time > 0 and event_time < 2**31:
                # Assume seconds
                timestamp = event_time
            elif event_time >= 2**31:
                # Assume milliseconds and convert to seconds
                timestamp = event_time / 1000
            else:
                return "00:00"

            # Format as MM:SS
            return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%M:%S")
        except (ValueError, OSError):
            return "00:00"

    @staticmethod
    def clear_terminal():
        """
        Clears the terminal screen for Windows, Mac, and Linux.
        """
        os.system("cls" if platform.system() == "Windows" else "clear")

    @staticmethod
    def restart_service(service_name: str):
        """
        Restart a systemd service using systemctl.
        """
        try:
            subprocess.run(["sudo", "systemctl", "restart", service_name], check=True)
            logger.debug(f"Service '{service_name}' restarted successfully.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart service '{service_name}'. Error: {e}")
            sys.exit(1)


    @staticmethod
    async def kill_process_on_port(port: int):
        """
        Find and kill any process running on a specified port.
        """
        try:
            # Use asyncio.create_subprocess_exec for asynchronous execution
            process = await asyncio.create_subprocess_exec(
                "lsof", "-i", f":{port}", "-t",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:  # Check if the command was successful
                pids = stdout.decode().strip().splitlines()
                if pids:
                    logger.info(f"Processes found on port {port}: {', '.join(pids)}. Killing them...")
                    for pid in pids:
                        try:
                            os.kill(int(pid), 9)
                            logger.info(f"Process {pid} killed successfully.")
                        except Exception as kill_error:
                            logger.error(f"Error killing process {pid}: {kill_error}")
                else:
                    logger.info(f"No process found on port {port}.")
            else:
                logger.info(f"Port {port} is free to use!")

        except Exception as e:
            logger.error(f"Error occurred while killing process on port {port}: {e}")

    @staticmethod
    def show_progress(current, total, symbol, interval):
        """
        Displays a progress bar in the console.
        """
        progress = (current / total) * 100
        bar_length = 20
        filled_length = int(bar_length * progress // 100)
        bar = "█" * filled_length + "-" * (bar_length - filled_length)
        print(f"Progress: [{bar}] {progress:.1f}% complete", end="\r")

    @staticmethod
    def get_crypto(symbol):
        return AppConfig.bot.products.cryptos[symbol.upper()]

    @staticmethod
    def add_task(task):
        AppConfig.tasks.append(task)

    @staticmethod
    async def cancel_tasks():
        for task in AppConfig.tasks:
            task.cancel()
        await asyncio.gather(*AppConfig.tasks, return_exceptions=True)
        AppConfig.tasks.clear()
        logger.info("All tasks cancelled.")


    @staticmethod
    def update_bot_info(func):
        if AppConfig.bot is not None:
            AppConfig.bot_info.number_of_cryptos = len(AppConfig.bot.products.cryptos)
            AppConfig.bot_info.number_of_active_orders = len(AppConfig.bot.order_manager.open_orders)
            AppConfig.bot_info.current_usdt_balance = AppConfig.bot.order_creator.current_usdt_balance
            AppConfig.bot_info.placed_usdt_amount = AppConfig.bot.order_creator.placed_usdt_amount

