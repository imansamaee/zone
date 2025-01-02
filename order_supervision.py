#TODO fix this and apply it. no current use.

import asyncio
from app_config import AppConfig
from loguru import logger

class PairSupervision:
    def __init__(self, pair):
        self.pair = pair

    
    def check_buy_order(self):
        self.ckeck_current_price
