from datetime import datetime
from models.zone import Zone


class ZoneManager:
    def __init__(self, klines):
        self.klines = klines
        self.last_demand_zone = None
        self.last_supply_zone = None
        self.consecutive_green_solid_klines = []
        self.immediate_demand_zone = None
        self.supply_zone_before_immediate_demand_zone = None
        self.is_previous_structure_broken = False
        self._initialize_zones()

    def _initialize_zones(self):
        """
        Initializes the last demand and supply zones based on the latest Kline data.
        """
        for i in range(len(self.klines) - 3, 1, -1):  # Iterate backward through klines
            current_kline = self.klines[i]
            previous_kline = self.klines[i - 1]
            next_kline = self.klines[i + 1]

            try:
                creation_time = datetime.fromtimestamp(
                    current_kline[0] / 1000
                )  # Convert ms to seconds
            except (ValueError, OSError):
                print(f"Invalid timestamp in Kline: {current_kline[0]}")
                continue  # Skip invalid timestamps

            # Identify a demand zone (Drop-Base-Rally)
            if (
                current_kline[3]
                < previous_kline[3]  # Current low is lower than previous low
                and current_kline[3]
                < next_kline[3]  # Current low is lower than next low
            ):
                self.last_demand_zone = Zone(
                    zone_type="demand",
                    low=current_kline[3],  # Low price
                    high=current_kline[3] * 1.01,  # Add 1% buffer
                    creation_time=creation_time,
                    candles=self.klines[max(0, i - 3) : i + 1],
                    klines=self.klines,
                )
                break

            # Identify a supply zone (Rally-Base-Drop)
            if (
                current_kline[2]
                > previous_kline[2]  # Current high is higher than previous high
                and current_kline[2]
                > next_kline[2]  # Current high is higher than next high
            ):
                self.last_supply_zone = Zone(
                    zone_type="supply",
                    low=current_kline[2] * 0.99,  # Subtract 1% buffer
                    high=current_kline[2],  # High price
                    creation_time=creation_time,
                    candles=self.klines[max(0, i - 3) : i + 1],
                    klines=self.klines,
                )
                break

        # After initializing zones, find consecutive green solid Klines
        self.consecutive_green_solid_klines = self.find_consecutive_green_solid_klines(
            min_consecutive=3, wicks_ratio=4, min_percentage=1.0
        )

        # Identify immediate demand zone after green streaks
        if self.consecutive_green_solid_klines:
            self.immediate_demand_zone = self.locate_prior_demand_zone(
                self.consecutive_green_solid_klines,
                base_candle_count=3,
                zone_buffer=0.01,
            )

        # Locate the last supply zone before the immediate demand zone
        if self.immediate_demand_zone:
            self.supply_zone_before_immediate_demand_zone = (
                self.locate_prior_supply_zone()
            )

        # Check if the previous structure is broken
        if self.immediate_demand_zone:
            self.is_previous_structure_broken = self.check_prior_structure_broken()

    def find_consecutive_green_solid_klines(
        self, min_consecutive=3, wicks_ratio=4, min_percentage=1.0
    ):
        """
        Finds consecutive green solid Klines with minimal wicks and a percentage price increase.

        Args:
            min_consecutive (int): Minimum number of consecutive green Klines to detect.
            wicks_ratio (int): Maximum wick-to-body ratio allowed for a candle to be considered solid.
            min_percentage (float): Minimum percentage increase from open to close required for a candle.

        Returns:
            list of list: A list of consecutive green Klines meeting the criteria.
        """
        consecutive_green_solid_klines = []
        current_streak = []

        for kline in self.klines:
            # Extract prices using list indices
            open_price = kline[1]
            high_price = kline[2]
            low_price = kline[3]
            close_price = kline[4]

            # Calculate body and wick sizes
            body_size = abs(close_price - open_price)
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low_price

            # Calculate percentage increase
            percentage_increase = ((close_price - open_price) / open_price) * 100

            # Check if the Kline is green, solid, and meets the percentage increase condition
            is_green = close_price > open_price
            has_small_wicks = (
                upper_wick <= body_size / wicks_ratio
                and lower_wick <= body_size / wicks_ratio
            )
            meets_percentage = percentage_increase >= min_percentage

            if is_green and has_small_wicks and meets_percentage:
                current_streak.append(kline)

                # Save streak if it meets the minimum criteria
                if len(current_streak) >= min_consecutive:
                    consecutive_green_solid_klines.append(list(current_streak))
            else:
                # Reset streak on invalid Kline
                current_streak = []

        return consecutive_green_solid_klines

    def locate_prior_demand_zone(
        self, green_streaks, base_candle_count=3, zone_buffer=0.01
    ):
        """
        Finds the immediate demand zone before a streak of consecutive green solid Klines.

        Args:
            green_streaks (list of list): List of green streaks identified earlier.
            base_candle_count (int): Number of candles to use for the base of the demand zone.
            zone_buffer (float): Percentage buffer above the low of the base for the demand zone's upper boundary.

        Returns:
            Zone or None: A Zone object representing the demand zone or None if no valid zone is found.
        """
        if not green_streaks:
            return None

        # Get the first streak
        first_streak = green_streaks[0]
        first_candle = first_streak[0]  # The first candle of the streak

        # Find the base candles immediately before the streak
        end_index = self.klines.index(first_candle)  # Get index of the first candle
        start_index = max(
            0, end_index - base_candle_count
        )  # Ensure we don't go out of bounds
        base_candles = self.klines[start_index:end_index]

        if len(base_candles) < base_candle_count:
            return None  # Not enough candles to form a base

        # Calculate the demand zone
        base_low = min(candle[3] for candle in base_candles)  # Lowest price in the base
        demand_zone = Zone(
            zone_type="demand",
            low=base_low,
            high=base_low * (1 + zone_buffer),  # Add buffer above the low
            creation_time=datetime.now(),
            candles=base_candles,
            klines=self.klines,
        )

        return demand_zone

    def locate_prior_supply_zone(self):
        """
        Finds the last supply zone before the immediate demand zone.

        Returns:
            Zone or None: The supply zone found before the immediate demand zone or None.
        """
        if not self.immediate_demand_zone:
            return None

        # Iterate backward to find the prior supply zone
        for i in range(len(self.klines) - 1, -1, -1):
            kline = self.klines[i]
            if (
                kline[2]
                > self.immediate_demand_zone.high  # High is greater than the immediate demand zone's high
            ):
                return Zone(
                    zone_type="supply",
                    low=kline[2] * 0.99,
                    high=kline[2],
                    creation_time=datetime.fromtimestamp(kline[0] / 1000),
                    candles=[kline],
                    klines=self.klines,
                )
        return None

    def check_prior_structure_broken(self):
        """
        Checks if the last supply zone before the prior demand zone is broken by the current price action.

        Returns:
            bool: True if the previous structure is broken, False otherwise.
        """
        if not self.supply_zone_before_immediate_demand_zone:
            return False

        # Check if the structure of the supply zone is broken
        for kline in self.klines:
            close_price = kline[4]
            if (
                close_price > self.supply_zone_before_immediate_demand_zone.high
            ):  # Price breaks above the supply zone
                return True

        return False