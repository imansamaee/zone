from pydantic import BaseModel


class BotInfo(BaseModel):
    bot_is_running: bool = False
    number_of_cryptos: int = 0
    number_of_active_orders: int = 0
    current_usdt_balance: float = 0.0
    placed_usdt_amount: float = 0.0