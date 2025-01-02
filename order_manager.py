import asyncio
from collections import defaultdict
import ccxt
from app_config import AppConfig
from loguru import logger


class BinanceOrder:
    def __init__(self, binance_order_dict):
        if not binance_order_dict:
            return
        for key, value in binance_order_dict.items():
            if isinstance(value, dict):  # Check if the value is a dictionary
                setattr(
                    self, key, BinanceOrder(value)
                )  # Recursively create a class for the nested dictionary
            else:
                setattr(self, key, value)
        self.original_dict = binance_order_dict
        self.sell_price = 0.0
        self.stop_loss_price = 0.0
        self.id = None


class OrderManager:
    def __init__(self):
        self.current_USDT_amount = 0
        self.open_orders = {}
        self.order_history = []
        self.active_symbols = []
        self.pnl_per_symbol = defaultdict(float)
        self.exchange = ccxt.binance(
            {
                "apiKey": AppConfig.API_KEY,
                "secret": AppConfig.API_SECRET,
                "enableRateLimit": True,
            }
        )
        self.exchange.load_markets()
        if AppConfig.convert_assets:
            self.convert_all_assets_to_quote_currency()

    def get_order_status(self, order_id):
        """
        Get the status of an order. Includes logging.
        """
        try:
            logger.debug(f"Fetching status for order {order_id}")
            order = self.open_orders.get(order_id)
            if order:
                return order.info.status  # Access status from the BinanceOrder object
            else:
                logger.warning(f"Order not found: {order_id}")
                return None
        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            return None

    def cancel_order(self, order_id):
        """
        Cancel an order. Includes logging.
        """
        try:
            logger.info(f"Attempting to cancel order {order_id}")
            order = self.open_orders.get(order_id)
            if order:
                # Use AppConfig to access the Binance client and cancel the order
                AppConfig.binance_client.cancel_order(
                    symbol=order.symbol, orderId=order_id
                )
                order.info.status = "CANCELED"
                self.remove_order(order_id)
                logger.info(f"Canceled order: {order_id}")
            else:
                logger.warning(f"Order not found: {order_id}")
        except Exception as e:
            logger.error(f"Error canceling order: {e}")

    def get_pnl_for_symbol(self, symbol):
        """
        Get the PNL for a specific symbol.
        """
        return self.pnl_per_symbol.get(symbol, 0)

    def market_sell_by_id(self, order_id):
        """
        Sells the asset associated with the given order ID at market price.
        """
        try:
            order = self.open_orders.get(order_id)
            if order:
                AppConfig.binance_client.create_order(
                    symbol=order.symbol,
                    type="MARKET",
                    side="SELL",
                    quantity=order.amount,
                )
                logger.info(
                    f"Successfully sold {order.symbol} (order ID: {order_id}) at market price."
                )  # More informative log
            else:
                logger.warning(
                    f"Order with ID {order_id} not found for market sell."
                )  # More specific log
        except Exception as e:
            logger.error(
                f"Error selling asset (order ID: {order_id}) at market price: {e}"
            )  # Include order ID in error log

    async def  add_order(
        self,
        order_dict,
        side="",
        sell_price=None,
        buy_order_id=None,
        stop_loss_price=None,
    ):
        """
        Adds a Binance order dictionary, converts it to BinanceOrder,
        and adds it to the open_orders dictionary. Handles errors and
        market selling if necessary.
        """
        try:
            order = BinanceOrder(order_dict)
            
            if "info" not in order_dict:
                _id = order_dict['orderId']
                _symbol = order_dict["symbol"]
                order_dict=self.exchange.fetch_order(_id, _symbol)  

            order.id = order_dict["info"]["orderId"]
            order.symbol = order_dict["info"]["symbol"]
            order.sell_price = sell_price
            order.stop_loss_price = stop_loss_price
            order_id = order.id
            self.open_orders[order_id] = order
            self.order_history.append(order)
            logger.info(
                f"Added {side.upper()} order with ID {order_id} for {order.symbol} to open orders."
            )
            return order

        except Exception as e:
            logger.exception(
                f"Error adding order: {e}"
            )  # Use logger.exception to include traceback
            return None

    def remove_order(self, order_id):
        """
        Removes an order from open_orders.
        """
        try:
            if order_id in self.open_orders:
                self.open_orders.pop(order_id)
                logger.info(f"Removed order with ID {order_id} from open orders.")
            else:
                logger.warning(f"Order with ID {order_id} not found in open orders.")
        except Exception as e:
            logger.error(f"Error removing order: {e}")

    def is_order_open(self, order_id):
        """
        Checks if an order exists in the open_orders dictionary.
        """
        return order_id in self.open_orders

    def any_open_order_for_symbol(self, symbol):
        """
        Checks if there are any open orders for the given symbol.
        """
        for order_id, order in self.open_orders.items():
            if order.symbol == symbol:
                return True
        return False

    def update_order(self, order_id):
        """
        Updates an order with the exchange and updates open_orders if it's open.
        Returns the updated BinanceOrder object, or None if the order is not found or closed.
        """
        try:
            if order_id in self.open_orders:
                old_order = self.open_orders[order_id]  # Get the existing order

                updated_order_info = self.exchange.fetch_order(order_id, old_order.symbol)  
                updated_order = BinanceOrder(updated_order_info)
                updated_order.sell_price = old_order.sell_price
                updated_order.stop_loss_price = old_order.stop_loss_price
                updated_order.id = old_order.id
                updated_order.symbol = old_order.symbol.replace("/", "")
                return updated_order
            else:
                logger.warning(f"Order with ID {order_id} not found in open orders.")
                return None
        except Exception as e:
            logger.error(f"Error updating order: {e}")
            return None

    def convert_all_assets_to_quote_currency(self):
        """Convert all assets to quote currency."""
        logger.info("Converting all assets to quote currency...")
        try:

            balances = self.exchange.fetch_balance()["info"]["balances"]
        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
            return

        for balance in balances:
            asset = balance["asset"]
            if "USDT" == asset or float(balance["free"]) <= 0:
                continue

            symbol = asset + "USDT"
            logger.info(f"Converting {asset} to USDT")

            try:
                # Format the quantity to avoid LOT_SIZE errors
                formatted_quantity = self.exchange.amount_to_precision(
                    symbol, balance["free"]
                )

                # Place a market sell order
                self.exchange.create_order(
                    symbol=symbol.replace("USDT", "/USDT"),
                    type="market",
                    side="sell",
                    amount=formatted_quantity,
                )
            except Exception as e:
                logger.error(f"Error selling {symbol}: {e}")
