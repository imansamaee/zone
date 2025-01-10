import numpy as np
import pandas as pd
import ta

from app_config import AppConfig  # Assuming you have the 'ta' library installed


class TechnicalAnalysis:
    @staticmethod
    def calculate_ma(klines, period):
        close_prices = [kline[4] for kline in klines]  # Extract close prices
        close_prices_series = pd.Series(close_prices)  # Convert to Pandas Series
        return ta.trend.SMAIndicator(close_prices_series, window=period).sma_indicator()

    @staticmethod
    def calculate_rsi(klines, period=14):
        close_prices = [kline[4] for kline in klines]  # Extract close prices
        close_prices_series = pd.Series(close_prices)  # Convert to Pandas Series
        return ta.momentum.RSIIndicator(close_prices_series, window=period).rsi()
    
    @staticmethod
    def calculate_macd(klines, short_window=12, long_window=26, signal_window=9):
        """
        Calculates MACD and Signal Line for given kline data.

        Args:
            klines: A list of kline data (any timeframe). Each kline should be a list/tuple with at least the close price.
            short_window: The short EMA window (default is 12).
            long_window: The long EMA window (default is 26).
            signal_window: The signal line EMA window (default is 9).

        Returns:
            A dictionary containing:
                - "macd": Pandas Series representing the MACD line.
                - "signal": Pandas Series representing the Signal line.
                - "histogram": Pandas Series representing the MACD histogram.
        """
        close_prices = [kline[4] for kline in klines]  # Extract close prices
        close_prices_series = pd.Series(close_prices)  # Convert to Pandas Series

        macd = ta.trend.MACD(
            close_prices_series, 
            window_slow=long_window, 
            window_fast=short_window, 
            window_sign=signal_window
        )

        return {
            "macd": macd.macd(),
            "signal": macd.macd_signal(),
            "histogram": macd.macd_diff()
        }

    @staticmethod
    def is_uptrend_cover(klines_cover) -> bool:
        ma_5_cover = TechnicalAnalysis.calculate_ma(klines_cover, 5)
        ma_20_cover = TechnicalAnalysis.calculate_ma(klines_cover, 20)
        return bool(ma_5_cover.iloc[-1] > ma_20_cover.iloc[-1])  # Convert to bool

    @staticmethod
    def is_uptrend_1m(klines_1m) -> bool:
        ma_5_1m = TechnicalAnalysis.calculate_ma(klines_1m, 5)
        ma_20_1m = TechnicalAnalysis.calculate_ma(klines_1m, 20)
        return bool(ma_5_1m.iloc[-1] > ma_20_1m.iloc[-1])  # Convert to bool

    @staticmethod
    def find_support_resistance(klines, timeframe="1m"):
        """
        Identifies potential support and resistance levels with strength 
        values, using swing highs and lows calculated with NumPy.

        Args:
            klines: A list of kline data (any timeframe). Each kline 
                   should be a list/tuple with at least OHLC values 
                   (Open, High, Low, Close).
            timeframe: The timeframe of the kline data (e.g., '1m', AppConfig.cover_kline, '1d').
                       Used to adjust the swing detection sensitivity.

        Returns:
            A tuple containing two lists:
                - support_levels: A list of tuples, where each tuple is 
                                  (support_level, strength).
                - resistance_levels: A list of tuples, where each tuple is 
                                     (resistance_level, strength).
        """

        if not klines or len(klines[0]) < 4:
            raise ValueError("Invalid kline data provided.")

        closes = np.array([kline[4] for kline in klines])  # Get closing prices
        highs = np.array([kline[2] for kline in klines])
        lows = np.array([kline[3] for kline in klines])

        # Adjust swing shift based on timeframe
        if timeframe == AppConfig.cover_kline_interval:
            swing_shift = 2  
        else:  
            swing_shift = 1

        # Identify swing highs and lows using NumPy
        high_swing_indices = np.where(
            (highs > np.roll(highs, swing_shift)) & (highs > np.roll(highs, -swing_shift))
        )[0]
        low_swing_indices = np.where(
            (lows < np.roll(lows, swing_shift)) & (lows < np.roll(lows, -swing_shift))
        )[0]


        # Filter close resistance levels, keeping only the highest
        resistance_levels = []
        temp_level = None
        for level in highs[high_swing_indices]:
            if temp_level is None:
                temp_level = level
            elif level > temp_level:
                temp_level = level
            elif level < temp_level - 10:  # Adjust 10 to control closeness threshold
                resistance_levels.append(temp_level)
                temp_level = level
        if temp_level is not None:
            resistance_levels.append(temp_level)

        resistance_levels = TechnicalAnalysis._filter_close_levels(
            highs[high_swing_indices], closes, AppConfig.resistance_closeness_threshold_pct, "resistance"
        )
        support_levels = TechnicalAnalysis._filter_close_levels(
            lows[low_swing_indices], closes, AppConfig.support_closeness_threshold_pct, "support"
        )

        # Convert strength values to int
        resistance_levels = [(level, int(strength)) for level, strength in resistance_levels]
        support_levels = [(level, int(strength)) for level, strength in support_levels]

        return support_levels, resistance_levels
    
    @staticmethod
    def _filter_close_levels(levels, closes, threshold_pct, level_type):
        """
        Filters close levels and calculates strength.
        """
        filtered_levels = []
        temp_level = None
        temp_strength = 0
        threshold_multiplier = 1 - threshold_pct / 100 if level_type == "resistance" else 1 + threshold_pct / 100
        for level in levels:
            if temp_level is None:
                temp_level = level
                temp_strength = np.sum(np.isclose(closes, level, rtol=threshold_pct/100))  # Count close closes
            elif (level_type == "resistance" and level > temp_level) or \
                 (level_type == "support" and level < temp_level):
                temp_level = level
                temp_strength = np.sum(np.isclose(closes, level, rtol=threshold_pct/100))  # Count close closes
            elif (level_type == "resistance" and level < temp_level * threshold_multiplier) or \
                 (level_type == "support" and level > temp_level * threshold_multiplier):
                filtered_levels.append((temp_level, temp_strength))
                temp_level = level
                temp_strength = np.sum(np.isclose(closes, level, rtol=threshold_pct/100))  # Count close closes
        if temp_level is not None:
            filtered_levels.append((temp_level, temp_strength))
        return filtered_levels
