import asyncio
from dataclasses import dataclass, field

import binance
import ccxt
from app_config import AppConfig, TradingStrategy
from loguru import logger

from order_handler import OrderHandler
from utils import format_float, round_up_to_nearest


@dataclass
class OrderCandidate:
    symbol: str
    current_price: float
    support_level: float
    resistance_level: float
    price_filter: dict = field(default_factory=dict)
    limits: dict = field(default_factory=dict)


class OrderCreator:
    def __init__(self, order_manager, order_authorization, products):
        self.order_manager = order_manager
        self.order_authorization = order_authorization
        self.products = products
        self.current_usdt_balance = 0
        self.placed_usdt_amount = 0

    async def place_order(self, symbol, order_type, price, amount, side="buy"):
        """
        Places an order with the specified parameters.

        Args:
            candidate: The OrderCandidate object.
            order_type: The order type ('limit' or 'market').
            price: The order price (for limit orders).
            amount: The order amount.
        """
        try:
            order = self.order_manager.exchange.create_order(
                symbol=symbol,
                type=order_type,
                side=side,
                amount=amount,
                price=price if order_type == "limit" else None,
            )
            order_id = order["id"]
            logger.info(
                f"Placed {order_type.upper()} {side} order "
                f"for {symbol} with ID {order_id} at price {price if order_type == 'limit' else 'market'}"
            )
            return order
        except ccxt.NetworkError as e:
            logger.error(f"Network error: {e}")
        except ccxt.ExchangeError as e:
            error_message = str(e)
            logger.error(f"Exchange error: {e}")

            # Check for "Filter failure: NOTIONAL" error
            if "Filter failure: NOTIONAL" in error_message:
                logger.warning(
                    f"Adding {symbol} to blacklist due to NOTIONAL filter failure."
                )
                AppConfig.blacklist.add(symbol)  # Add symbol to blacklist

            # Check for "This symbol is not permitted for this account" error
            if "This symbol is not permitted for this account." in error_message:
                logger.warning(
                    f"Adding {symbol} to blacklist due to symbol not permitted error."
                )
                AppConfig.blacklist.add(symbol)  # Add symbol to blacklist

        except Exception as e:
            logger.exception(f"Error creating order: {e}")
        return None

    async def check_and_create_orders(self):
        """
        Continuously checks for order creation opportunities and creates limit orders.
        """
        logger.info("Checking for orders...")
        while not AppConfig.is_shutdown_initiated:
            try:
                self.current_usdt_balance = self.get_usdt_balance()
                number_of_posiible_orders = int(
                    self.current_usdt_balance / AppConfig.ORDER_USDT_AMOUNT
                )
                logger.info(f"Current USDT balance: {self.current_usdt_balance}")

                if self.current_usdt_balance >= AppConfig.ORDER_USDT_AMOUNT and (
                    AppConfig.MAX_USDT_TO_PLACE == 0
                    or self.placed_usdt_amount < AppConfig.MAX_USDT_TO_PLACE
                ):
                    candidates = self.get_order_candidates()
                    if not AppConfig.trading_strategy == TradingStrategy.SUSPEND:

                        for n, candidate in enumerate(candidates):
                            if n + 1 > number_of_posiible_orders:
                                break
                            asyncio.create_task(
                                self.create_buy_limit_order_for_candidate(candidate)
                            )
                    else:
                        logger.info("Trading is suspended by user.")

                else:
                    logger.info(
                        "Balance or limits check failed. Skipping order creation."
                    )

            except Exception as e:
                logger.exception(f"Error in check_and_create_orders: {e}")

            await asyncio.sleep(AppConfig.check_and_create_orders_interval)

    async def create_buy_limit_order_for_candidate(self, candidate):
        """
        Creates a limit order and handles filling/selling after the order is returned.
        """
        try:
            crypto = AppConfig.get_crypto(candidate.symbol)

            limit_prices = await self.calculate_limit_price(candidate)
            buy_limit_price = limit_prices[0]
            sell_limit_price = limit_prices[1]
            stop_loss_price = limit_prices[2]

            quantity = AppConfig.ORDER_USDT_AMOUNT / float(buy_limit_price)

            order_quantity = await self.calculate_order_quantity(
                candidate.symbol, candidate.limits, quantity
            )

            try:
                # Wait for place_order with a timeout
                order = await asyncio.wait_for(
                    self.place_order(
                        candidate.symbol, "limit", buy_limit_price, order_quantity
                    ),
                    timeout=10,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout while waiting for order placement.")
                return

            if order:
                binance_order = await self.order_manager.add_order(
                    order_dict=order,  # Specify order_dict
                    side="buy",  # Specify side
                    sell_price=sell_limit_price,  # Specify sell_price
                    buy_order_id=None,  # Specify buy_order_id (if applicable)
                    stop_loss_price=stop_loss_price,  # Specify stop_loss_price
                )
                order_handler = OrderHandler(
                    binance_order, self.order_manager, self
                )  # Create OrderHandler instance
                asyncio.create_task(
                    order_handler.handle_order_pair()
                )  # Start the order handling task
        except Exception as e:
            logger.exception(f"Error creating order: {e}")

    async def create_sell_limit_order_for_filled_order(self, binance_order):
        """
        Creates an OCO sell order (limit order with a stop-loss order)
        for a filled buy order. Retries up to 3 times in case of errors.
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:

                symbol = binance_order.symbol
                crypto = AppConfig.get_crypto(symbol)
                limits = crypto.limits
                amount = await self.calculate_order_quantity(
                    symbol, limits, binance_order.amount
                )
                sell_price = binance_order.sell_price
                stop_loss_price = binance_order.stop_loss_price
                logger.info(
                    f"Sell order details: symbol={symbol}, amount={amount}, stop_loss_price={stop_loss_price}, sell_price={sell_price}"
                )

                order = AppConfig.binance_client.order_oco_sell(
                    symbol=symbol,
                    abovePrice=sell_price,
                    quantity=amount,
                    aboveType="LIMIT_MAKER",
                    belowType="STOP_LOSS",
                    belowStopPrice=stop_loss_price,
                )
                # Log the successful order creation
                logger.info(
                    f"OCO sell order created successfully for {symbol} (ID: {order['orderListId']})."
                )
                return order  # Order placed successfully
            except binance.exceptions.BinanceAPIException as e:
                logger.warning(e)

                # Check for NOTIONAL filter failure
                if "Filter failure: NOTIONAL" in str(e):
                    logger.warning(
                        f"Adding {symbol} to blacklist due to NOTIONAL filter failure."
                    )
                    AppConfig.blacklist.add(symbol)

                # Check for symbol not permitted error
                elif (
                    e.code == -2010
                    and "This symbol is not permitted for this account." in str(e)
                ):
                    logger.warning(
                        f"Adding {symbol} to blacklist due to symbol not permitted error."
                    )
                    AppConfig.blacklist.add(symbol)

                if (
                    e.code == -2010
                ):  # Insufficient balance or incorrect price relationship
                    if "insufficient balance" in str(e).lower():
                        logger.warning(
                            f"Insufficient balance to create OCO sell order for {binance_order.symbol}."
                        )
                    elif "relationship of the prices" in str(e).lower():
                        logger.warning(
                            f"Invalid price relationship for OCO sell order for {binance_order.symbol}."
                        )
                    # You might want to add more specific handling for each case here

                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                    else:
                        logger.error(
                            f"Failed to create OCO sell order after {max_retries} attempts. Selling at market price."
                        )
                        try:
                            # Sell at market price
                            AppConfig.binance_client.create_order(
                                symbol=symbol,
                                type="MARKET",
                                side="SELL",
                                quantity=amount,  # Assuming binance_order has the amount
                            )
                        except Exception as market_sell_error:
                            logger.exception(
                                f"Error selling {binance_order.symbol} at market price: {market_sell_error}"
                            )
                else:
                    logger.error(
                        f"Error creating OCO sell order (attempt {attempt+1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2**attempt)
                    else:
                        logger.exception(
                            f"Failed to create OCO sell order after {max_retries} attempts."
                        )

            except Exception as e:
                logger.error(
                    f"Error creating OCO sell order (attempt {attempt+1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff (optional)
                else:
                    logger.exception(
                        f"Failed to create OCO sell order after {max_retries} attempts."
                    )
                    # Consider raising the exception or handling the failure differently

    async def calculate_order_quantity(
        self, candidate_symbol, candidate_limits, quantity
    ):
        """
        Calculates the order quantity based on the USDT amount and price,
        applying necessary rounding and minimum quantity checks.
        """

        # Apply precision rounding (this handles the precision)
        quantity = quantity * (1 - (AppConfig.binance_cost_pct / 100))
        quantity = self.order_manager.exchange.amount_to_precision(
            candidate_symbol, quantity
        )

        # Ensure quantity meets minimum order size
        min_quantity = candidate_limits["amount"]["min"]
        quantity = max(float(quantity), float(min_quantity))

        return format_float(str(quantity))

    async def calculate_limit_price(self, candidate):
        """
        Calculates the limit order price, considering the PERCENT_PRICE_BY_SIDE filter
        and market precision.
        """
        crypto = AppConfig.get_crypto(candidate.symbol)

        if (
            AppConfig.trading_strategy == TradingStrategy.TEST
            or AppConfig.trading_strategy == TradingStrategy.FLASH
        ):
            buy_limit_price = round_up_to_nearest(
                crypto.current_price * (1 + (8 * AppConfig.flash_pct / 100)),
                crypto.price_precision,
            )
            sell_limit_price = round_up_to_nearest(
                crypto.current_price * (1 + AppConfig.flash_pct / 100),
                crypto.price_precision,
            )
            stop_loss_price = round_up_to_nearest(
                crypto.current_price * (1 - (4 * AppConfig.flash_pct / 100)),
                crypto.price_precision,
            )
            return (
                buy_limit_price,
                sell_limit_price,
                stop_loss_price,
            )

        elif AppConfig.trading_strategy == TradingStrategy.SUPPORT_RESISTANCE:
            try:
                
                lowest_support = crypto.lowest_support_1m
                price_offset = 0.02 * (
                    candidate.resistance_level - candidate.support_level
                )

                # Calculate limit price based on side

                buy_limit_price = crypto.strongest_support_resistance[0] + price_offset
                buy_limit_price = round_up_to_nearest(
                    buy_limit_price, crypto.price_precision
                )
                sell_limit_price = crypto.strongest_support_resistance[1] - price_offset
                sell_limit_price = round_up_to_nearest(
                    sell_limit_price, crypto.price_precision
                )
                stop_loss_price = lowest_support - price_offset
                stop_loss_price = round_up_to_nearest(
                    stop_loss_price, crypto.price_precision
                )

                logger.info(
                    f"Calculated limit price for {candidate.symbol}: buy: {buy_limit_price}, sell: {sell_limit_price}"
                )

                return (
                    buy_limit_price,
                    sell_limit_price,
                    stop_loss_price,
                )

            except Exception as e:
                logger.exception(f"Error calculating limit price: {e}")
                return None  # Return None on error

    def get_usdt_balance(self):
        """
        Retrieves the current USDT balance.
        """
        try:
            balance = self.order_manager.exchange.fetch_balance()
            return balance["USDT"]["free"]
        except Exception as e:
            logger.exception("Error fetching USDT balance:")
            raise

    def get_order_candidates(self):
        """
        Gets order candidates using OrderAuthorization.
        If no nominees, uses the first crypto.
        """
        logger.info("Fetching order candidates...")
        nominees = self.order_authorization.get_nominees()
        if nominees:
            logger.info(
                f"{len(nominees)} nominees found: {[c["symbol"] for c in nominees]}"
            )
            candidates = []
            for nominee in nominees:  # Iterate through nominees
                crypto = self.products.cryptos[nominee["symbol"]]
                candidates.append(
                    OrderCandidate(
                        symbol=nominee["symbol"],
                        current_price=crypto.current_price,
                        support_level=nominee["support_level"],
                        resistance_level=nominee["resistance_level"],
                        price_filter=crypto.price_filter,
                        limits=crypto.limits,
                    )
                )
            return candidates
        else:
            logger.info("No candidates found.")
            return []
