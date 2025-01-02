import asyncio
from datetime import datetime, timezone
import json
import os

import ccxt
from loguru import logger
from app_config import AppConfig
from kline_fetcher import KlineFetcher


class OrderHandler:
    def __init__(self, buy_order, order_manager, order_creator):
        self.symbol = buy_order.symbol
        self.order_creator = order_creator
        self.buy_order = buy_order
        self.order_manager = order_manager
        self.sell_order_stop_loss = None
        self.sell_order_limit_marker = None
        self.pair_handling_is_cancelled = False  # Fixed typo
        crypto_dict = {
            key: value
            for key, value in AppConfig.get_crypto(self.symbol).dict().items()
            if key not in ("klines_1m", "klines_cover")
        }

        self.results = {
            "authorization_time": datetime.now(timezone.utc).isoformat(),  
            "crypto": crypto_dict,
        }
        self.filled_order_type = None
        self.pnl = 0.0

    async def handle_order_pair(self):
        """Handles a buy and sell order pair sequentially."""
        try:
            crypto = AppConfig.get_crypto(self.symbol)
            self.order_manager.active_symbols.append(self.symbol)
            if self.pair_handling_is_cancelled:
                return
            await self.handle_buy_order()
            if self.pair_handling_is_cancelled:
                return
            await asyncio.sleep(2)
            await self.handle_sell_order()
            if self.pair_handling_is_cancelled:
                return
            self.calculate_pnl()
        finally:

            if self.buy_order:
                self.order_manager.remove_order(self.buy_order.id)
            if self.sell_order_stop_loss:
                self.order_manager.remove_order(self.sell_order_stop_loss.id)
            if self.sell_order_limit_marker:
                self.order_manager.remove_order(self.sell_order_limit_marker.id)

            while self.symbol in self.order_manager.active_symbols:
                self.order_manager.active_symbols.remove(self.symbol)

            if self.pair_handling_is_cancelled:
                return
            await self.save_results()  # Save results even if errors occur

    async def handle_buy_order(self):
        """Handles the lifecycle of a buy order."""
        order = self.buy_order
        try:
            buy_order_id = order.id

            while (
                not AppConfig.is_shutdown_initiated
                and not self.pair_handling_is_cancelled
            ):
                try:
                    buy_order = self.order_manager.update_order(buy_order_id)
                    self.buy_order = buy_order
                    if not buy_order:
                        logger.info(
                            f"Buy order {buy_order_id} not found in open_orders. It was probably filled or canceled."
                        )  # More informative log
                        return  # Exit if the order is not found

                    if buy_order.info.status == "FILLED":
                        logger.info(
                            f"{buy_order.symbol} buy order {buy_order_id} is Filled."
                        )
                        try:
                            order_dict = await self.order_creator.create_sell_limit_order_for_filled_order(
                                buy_order
                            )
                            if not order_dict:
                                self.pair_handling_is_cancelled = True
                                return
                            for order in order_dict["orderReports"]:
                                new_order = await self.order_manager.add_order(
                                    order_dict=order,
                                    side="sell",
                                    sell_price=None,
                                    buy_order_id=buy_order_id,
                                    stop_loss_price=None,
                                )
                                if order["type"] == "STOP_LOSS":
                                    self.sell_order_stop_loss = new_order
                                if order["type"] == "LIMIT_MAKER":
                                    self.sell_order_limit_marker = new_order

                        except Exception as e:
                            logger.exception(
                                f"Error creating sell order for filled buy order: {e}"
                            )
                            break  # Break the loop on error

                    elif buy_order.info.status == "CANCELED":
                        logger.info(f"Buy order {buy_order_id} was canceled.")
                        self.pair_handling_is_cancelled = True
                        return  # Exit the loop if the buy order is canceled

                    if self.sell_order_stop_loss and self.sell_order_limit_marker:
                        return
                    await asyncio.sleep(AppConfig.check_buy_order_wait)

                except ccxt.NetworkError as network_err:
                    logger.error(
                        f"Network error while updating buy order: {network_err}"
                    )
                    await asyncio.sleep(5)
                except Exception as e:
                    logger.exception(f"Error handling buy order in loop: {e}")
                    break  # Break the loop on error

        except Exception as e:
            logger.exception(f"Error handling buy order (outer try): {e}")

        finally:
            logger.info(
                f"handle_buy_order finalized for {self.symbol}."
            )  # Include symbol in log

    async def handle_sell_order(self):
        """Handles the lifecycle of a sell order."""
        while not AppConfig.is_shutdown_initiated:

            self.sell_order_limit_marker
            try:
                while not AppConfig.is_shutdown_initiated:

                    sell_order_stop_loss = self.order_manager.update_order(
                        self.sell_order_stop_loss.id
                    )
                    self.sell_order_stop_loss = sell_order_stop_loss
                    sell_order_limit_marker = self.order_manager.update_order(
                        self.sell_order_limit_marker.id
                    )
                    self.sell_order_limit_marker = sell_order_limit_marker

                    if sell_order_stop_loss.info.status == "FILLED":
                        self.filled_order_type = "STOP_LOSS"
                        logger.info(
                            f"Stop-loss order filled for {sell_order_stop_loss.symbol}"
                        )  # Log stop-loss filled
                        return

                    if sell_order_limit_marker.info.status == "FILLED":
                        self.filled_order_type = "LIMIT_MAKER"
                        logger.info(
                            f"Limit order filled for {sell_order_limit_marker.symbol}"
                        )  # Log limit order filled
                        return

                    if (
                        sell_order_limit_marker.info.status == "CANCELED"
                        or sell_order_stop_loss.info.status == "CANCELED"
                    ):
                        logger.info(f"Sell order CANCELED...")
                        self.pair_handling_is_cancelled = True
                        return

                    await asyncio.sleep(AppConfig.check_sell_order_wait)
            except Exception as e:
                logger.exception(f"Error handling sell order: {e}")

    def calculate_pnl(self):
        """
        Calculates and updates the PNL for a filled sell order pair,
        including Binance fees.
        """
        try:
            buy_order = self.buy_order
            if self.filled_order_type == "STOP_LOSS":
                sell_order = self.sell_order_stop_loss
            if self.filled_order_type == "LIMIT_MAKER":
                sell_order = self.sell_order_limit_marker
            if buy_order and sell_order:

                pnl = (
                    (sell_order.average * sell_order.amount)
                    * (1 - AppConfig.binance_cost_pct / 100)
                    - (buy_order.average * buy_order.amount)
                    * (1 - AppConfig.binance_cost_pct / 100)
                    + (buy_order.amount - sell_order.amount) * sell_order.average
                )
                self.pnl = pnl

                self.order_manager.pnl_per_symbol[sell_order.symbol] += pnl
                logger.info(
                    f"PNL for order pair ({sell_order.symbol}): {pnl}, "
                    f"Overall PNL: {self.order_manager.pnl_per_symbol[sell_order.symbol]}"
                )
            else:
                logger.warning(
                    f"Buy order or sell order not found for PNL calculation."
                )

        except Exception as e:
            logger.exception(f"Error calculating PNL: {e}")

    async def save_results(self):
        """Saves crypto and order data to a JSON file."""
        try:
            # Prepare data for JSON
            order_data = {
                "symbol": self.symbol,
                "buy_order": self.buy_order.original_dict,
                "sell_order_stop_loss": (
                    self.sell_order_stop_loss.original_dict
                    if self.sell_order_stop_loss
                    else None
                ),
                "sell_order_limit_marker": (
                    self.sell_order_limit_marker.original_dict
                    if self.sell_order_limit_marker
                    else None
                ),
                "timestamp":datetime.now(timezone.utc).isoformat(), # i want this time to be in GTC
            }
            self.results["order"] = order_data
            self.results["pnl"] = self.pnl


            crypto = AppConfig.get_crypto(self.symbol)
            crypto.klines_1m = KlineFetcher.fetch_symbol_historical_data(self.symbol, "1m")
            crypto.klines_cover = KlineFetcher.fetch_symbol_historical_data(self.symbol, AppConfig.cover_kline_interval)

            # Convert klines to lists of lists of floats
            crypto.klines_1m = [[float(v) for v in kline] for kline in crypto.klines_1m]
            crypto.klines_cover = [[float(v) for v in kline] for kline in crypto.klines_cover] 

            await asyncio.sleep(5)

            self.results["trade_time_crypto"] = crypto.dict()


            # Create the 'static/pairs_history' folder if it doesn't exist
            pairs_dir = os.path.join("static", "pairs_history")  # Updated path
            if not os.path.exists(pairs_dir):
                os.makedirs(pairs_dir)

            # Save to JSON file in the 'static/pairs_history' folder
            filename = os.path.join(
                pairs_dir,
                f"order_{self.symbol}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.json",
            )

            with open(filename, "w") as jsonfile:
                json.dump(
                    self.results,
                    jsonfile,
                    indent=4,
                )

            logger.info(f"Crypto and order data saved to {filename}")

        except Exception as e:
            logger.error(f"Error saving data to JSON: {e}")
