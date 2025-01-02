from loguru import logger

from app_config import AppConfig, TradingStrategy


class OrderAuthorization:
    def __init__(self, crypto_data, volatility_threshold):
        """
        Initialize with crypto data and volatility threshold.
        """
        self.crypto_data = crypto_data
        self.volatility_threshold = volatility_threshold
        self.nominees = []

    def test_black_list(self, crypto):
        """Tests if the crypto is in the blacklist."""
        if crypto.symbol in AppConfig.blacklist:
            return "failed"
        else:
            return "passed"

    def test_trend(self, crypto):
        """Tests if the crypto is in an uptrend on both cover and 1m timeframes."""
        if crypto.is_uptrend_cover and crypto.is_uptrend_1m:
            return "passed"
        else:
            return "failed"

    def test_support_resistance(self, crypto):
        """Tests if the crypto has valid support and resistance levels."""
        next_support, next_resistance = crypto.next_support_resistance
        if next_resistance == 0 or next_support == 0:
            return "failed"
        if not (crypto.lowest_support_1m < next_support and next_support < crypto.current_price and crypto.current_price < next_resistance):
            return "failed"
        else:
            return "passed"

    def test_range(self, crypto):
        """Tests if the crypto's support_resistance_1m_range_pct is reasonable."""
        # Directly access the crypto's range pct and check if it's unusual
        if crypto.is_unusual_volatility:
            return "failed"
        else:
            return "passed"

    def test_sr_gap_pct(self, crypto):
        """Tests if the crypto's support_resistance_1m_range_pct is reasonable."""
        # Directly access the crypto's range pct and check if it's unusual
        if crypto.support_resistance_range_pct < AppConfig.min_sr_gap_pct:
            return "failed"
        else:
            return "passed"

    def test_volatility(self, crypto):
        """
        Tests if the crypto's volatility for both 1m and cover
        falls within the defined thresholds in AppConfig.volatility.
        """
        if (
            AppConfig.volatility["one_m_low"]
            <= crypto.volatility_factor_1m
            <= AppConfig.volatility["one_m_high"]
            and AppConfig.volatility["one_h_low"]
            <= crypto.volatility_factor_cover
            <= AppConfig.volatility["one_h_high"]
        ):
            return "passed"
        else:
            return "failed"

    def test_active_orders(self, crypto):
        """Tests if the crypto has any open orders."""
        # Assuming you have a way to access open orders for a specific symbol
        # For example, using the OrderManager:
        if crypto.symbol in AppConfig.bot.order_manager.active_symbols:
            return "failed"  # Or "passed" if you WANT open orders
        else:
            return "passed"

    def get_nominees(self):
        """
        Identify nominee cryptos based on criteria, using test functions.z
        Adapts to additional test functions automatically.
        Uses the 'apply' attribute in test functions to determine
        if they should be applied to the nomination process.

        :return: List of cryptos with symbol, support, resistance, and volatility.
        """

        nominees = []
        sorted_cryptos = sorted(
            self.crypto_data.values(),
            key=lambda crypto: crypto.last_volume,
            reverse=True,
        )
        for crypto in sorted_cryptos:
            crypto_is_passed = False
            test_functions = [
                func_name
                for func_name in dir(self)
                if func_name.startswith("test_") and callable(getattr(self, func_name))
            ]

            test_results = {}
            for func_name in test_functions:
                test_func = getattr(self, func_name)
                # Check if the test function has the 'apply' attribute and it's True
                # No need for special handling of test_range anymore
                test_results[func_name] = test_func(crypto)

            AppConfig.bot.products.cryptos[crypto.symbol].test_results = test_results
            if (
                AppConfig.trading_strategy == TradingStrategy.TEST
                and self.test_active_orders(crypto) == "passed"
            ):
                crypto_is_passed = True

            if AppConfig.trading_strategy == TradingStrategy.SUPPORT_RESISTANCE and (
                all(test == "passed" for test in test_results.values())
            ):
                crypto_is_passed = True

            if (
                AppConfig.trading_strategy == TradingStrategy.FLASH
                and self.test_trend(crypto) == "passed"
                and self.test_active_orders(crypto) == "passed"
            ):
                crypto_is_passed = True

            if crypto_is_passed:
                next_support, next_resistance = crypto.next_support_resistance
                nominees.append(
                    {
                        "symbol": crypto.symbol,
                        "support_level": next_support,
                        "resistance_level": next_resistance,
                        "support_resistance_1m_range_pct": crypto.support_resistance_1m_range_pct,
                        "test_results": test_results,
                    }
                )

        self.nominees = nominees
        return nominees
