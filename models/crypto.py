from dataclasses import field
from datetime import datetime
from pydantic import BaseModel, Field, computed_field
from typing import Optional, List, Dict, Tuple
from technical_analysis import TechnicalAnalysis
from zone_manager import ZoneManager


class Crypto(BaseModel):
    symbol: str
    status: Optional[str] = ""
    base_asset: str
    quote_asset: str
    base_asset_unit: Optional[str] = ""
    quote_asset_unit: Optional[str] = ""
    minimum_quantity: float = Field(default=0.0, alias="minimum_quantity")
    tick_size: float = Field(default=0.0, alias="tick_size")
    base_asset_name: Optional[str] = ""
    quote_asset_name: Optional[str] = ""
    opening_price: float = 0.0
    high_price: float = 0.0
    low_price: float = 0.0
    current_price: float = 0.0
    base_asset_volume: float = 0.0
    quote_asset_volume: float = 0.0
    adjusted_volume: float = 0.0
    pair_market_type: Optional[str] = ""
    pair_market_name: Optional[str] = ""
    circulating_supply: Optional[float] = None
    price_filter: dict = {}
    price_precision: float
    limits: dict = {}
    filters: list = field(default_factory=list)
    tags: Optional[List[str]] = Field(default_factory=list)
    is_price_stable: bool = False
    last_volume: float = 0.0
    _old_price_movement: Optional[Tuple[float, int]] = (0.0, -1)  # Initialize as None
    _old_price: float = 0.0
    # I want klines to be printed last after @computed fields
    klines_1m: List[List[float]] = Field(
        default_factory=list
    )  # Add klines_1m attribute
    klines_cover: List[List[float]] = Field(
        default_factory=list
    )  # Add klines_cover attribute
    test_results: dict = {}  # Initialize test_results as an empty dictionary
    is_unusual_volatility: Optional[bool] = False

    @computed_field
    @property
    def current_time(self) -> int:
        return int(datetime.now().timestamp() * 1000)

    @computed_field
    @property
    def zones_1m(self) -> Tuple[dict, dict]:
        """Convert zones to dictionaries for storage in Crypto."""
        zone_manager = ZoneManager(self.klines_1m, "1m")
        supply_zones, demand_zones = zone_manager.supply_zones, zone_manager.demand_zones

        # Use the dict() method from Pydantic models to convert each zone to a dictionary
        supply_zones_dicts = [zone.dict() for zone in supply_zones]
        demand_zones_dicts = [zone.dict() for zone in demand_zones]

        return supply_zones_dicts, demand_zones_dicts

    @computed_field
    @property
    def zones_cover(self) -> Tuple[dict, dict]:
        """Convert cover zones to dictionaries for storage in Crypto."""
        zone_manager = ZoneManager(self.klines_cover, "cover")
        supply_zones, demand_zones = zone_manager.supply_zones, zone_manager.demand_zones

        # Use the dict() method from Pydantic models to convert each zone to a dictionary
        supply_zones_dicts = [zone.dict() for zone in supply_zones]
        demand_zones_dicts = [zone.dict() for zone in demand_zones]

        return supply_zones_dicts, demand_zones_dicts

    @computed_field
    @property
    def support_resistance_1m(
        self,
    ) -> tuple[list[tuple[float, int]], list[tuple[float, int]]]:
        """
        Calculates support and resistance levels for 1-minute kline data
        using the `find_support_resistance` method.

        Returns:
            A tuple containing two lists:
                 - support_levels: A list of tuples, where each tuple is
                                   (support_level, strength).
                 - resistance_levels: A list of tuples, where each tuple is
                                      (resistance_level, strength).
        """
        return TechnicalAnalysis.find_support_resistance(self.klines_1m, timeframe="1m")

    @computed_field
    @property
    def volatility_factor_1m(self) -> float:
        klines_1m = self.klines_1m
        high = max(kline[2] for kline in klines_1m)
        low = min(kline[3] for kline in klines_1m)
        return ((high - low) / low) * 100 if low != 0 else 0

    @computed_field
    @property
    def volatility_factor_cover(self) -> float:
        klines_cover = self.klines_cover
        high = max(kline[2] for kline in klines_cover)
        low = min(kline[3] for kline in klines_cover)
        return ((high - low) / low) * 100 if low != 0 else 0

    @computed_field
    @property
    def next_support_resistance(self) -> tuple[float, float]:

        supports, resistances = self.support_resistance_1m
        support, resistance = self.strongest_support_resistance

        if support == 0 or resistance == 0 or len(supports) < 2 or len(resistances) < 2:
            return (0, 0)
        resistances.sort(key=lambda item: item[0], reverse=True)
        resistance_level = resistances[1][0]
        return (support, resistance_level)

    @computed_field
    @property
    def strongest_support_resistance(self) -> tuple[float, float]:
        support_levels, resistance_levels = self.support_resistance_1m
        if len(support_levels) < 1 or len(resistance_levels) < 1:
            return (0, 0)

        # Extract price level (first element) from strongest levels
        strongest_support = max(support_levels, key=lambda item: item[1])[0]
        strongest_resistance = max(resistance_levels, key=lambda item: item[1])[0]

        return float(strongest_support), float(strongest_resistance)

    @computed_field
    @property
    def price_movement(self) -> Tuple[float, int]:
        """
        Calculates the price movement and its strength.

        Returns a tuple:
            - float: The price percentage difference
            - int: The strength of the movement (incremental, resets on turn)
        """
        current_price = self.current_price

        if self._old_price_movement is not None:
            old_price, old_strength = self._old_price_movement
            if old_price == 0:
                price_difference_pct = (
                    0.0  # Or handle it differently based on your logic
                )
            else:
                price_difference_pct = ((current_price - old_price) / old_price) * 100
        else:
            price_difference_pct = 0.0  # Initial value
            old_strength = 0

        if price_difference_pct > 0 and old_strength < 0:  # Turn from down to up
            strength = 1  # Reset strength to 1
        elif price_difference_pct < 0 and old_strength > 0:  # Turn from up to down
            strength = -1  # Reset strength to -1
        elif price_difference_pct > 0:  # Continued upward movement
            strength = old_strength + 1
        elif price_difference_pct < 0:  # Continued downward movement
            strength = old_strength - 1
        else:
            strength = 0  # No price change

        self._old_price_movement = (current_price, strength)  # Store current values
        return price_difference_pct, strength  # Return percentage difference

    # @computed_field
    # @property
    # def is_price_going_down_to_support(self) -> bool:
    #     """Checks if the price is moving down towards the strongest support."""
    #     support = self.strongest_support_resistance[0]
    #     if self.current_price > support:
    #         # Calculate the price difference between the current price and the support level
    #         price_difference = self.current_price - support

    #         # Calculate the percentage decrease from the current price to the support level
    #         percentage_decrease = (price_difference / self.current_price) * 100

    #         # Check if the percentage decrease is greater than a certain threshold (e.g., 2%)
    #         if percentage_decrease > 2:  # You can adjust this threshold as needed
    #             return True

    #     return False

    @computed_field
    @property
    def support_resistance_range_pct(self) -> float:
        """
        Calculates the percentage difference between the next resistance
        and next support levels.
        """
        next_support, next_resistance = (
            self.next_support_resistance
        )  # Directly unpack the tuple
        if next_support == 0 or next_resistance == 0:
            return 0

        gap_pct = ((next_resistance - next_support) / next_support) * 100
        return gap_pct

    @computed_field
    @property
    def is_uptrend_cover(self) -> bool:
        return TechnicalAnalysis.is_uptrend_cover(
            self.klines_cover
        )  # Use the TechnicalAnalysis method

    @computed_field
    @property
    def is_uptrend_1m(self) -> bool:
        return TechnicalAnalysis.is_uptrend_1m(
            self.klines_1m
        )  # Use the TechnicalAnalysis method

    @computed_field
    @property
    def support_resistance_1m_range_pct(self) -> float:
        """
        Calculates the pct range between the next support and resistance
        levels relative to the current price, based on 1-minute kline data.

        Returns:
            The pct range between support and resistance levels.
        """
        next_support, next_resistance = self.next_support_resistance  # Directly unpack

        if next_support and next_resistance:
            range_pct = ((next_resistance - next_support) / next_support) * 100
            return range_pct
        else:
            return 0

    @computed_field
    @property
    def lowest_support_1m(self) -> float:
        support_levels, _ = self.support_resistance_1m
        if len(support_levels) < 1:
            return 0
        return min(support_levels, key=lambda item: item[0])[0]

    @computed_field
    @property
    def next_to_lowest_support_pct(self) -> float:
        support = self.next_support_resistance[0]
        return (support - self.lowest_support_1m) / self.lowest_support_1m

    @computed_field
    @property
    def calculate_ma_rsi(self) -> Dict[str, float]:
        ma_period = 20
        rsi_period = 14

        return {
            "ma_1m": float(
                TechnicalAnalysis.calculate_ma(self.klines_1m, ma_period).iloc[-1]
            ),
            "ma_cover": float(
                TechnicalAnalysis.calculate_ma(self.klines_cover, ma_period).iloc[-1]
            ),
            "rsi_1m": float(
                TechnicalAnalysis.calculate_rsi(self.klines_1m, rsi_period).iloc[-1]
            ),
            "rsi_cover": float(
                TechnicalAnalysis.calculate_rsi(self.klines_cover, rsi_period).iloc[-1]
            ),
        }
