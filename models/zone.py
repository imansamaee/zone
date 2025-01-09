from pydantic import BaseModel, Field, computed_field
from typing import Literal, List
from datetime import datetime


class Zone(BaseModel):
    zone_type: Literal["demand", "supply"]  # Restrict zone type to "demand" or "supply"
    low: float = Field(..., description="Lowest price in the zone")
    high: float = Field(..., description="Highest price in the zone")
    creation_time: datetime = Field(..., description="Timestamp of zone creation")
    candles: List[List] = Field(
        ..., description="List of candlestick data in raw Kline format"
    )
    klines: List[List] = Field(
        default_factory=list, description="All Klines associated with the zone"
    )

    @computed_field
    @property
    def is_fresh(self) -> bool:
        """
        Checks if the zone is fresh (i.e., untouched by price action).

        Returns:
            bool: True if the zone is fresh, False otherwise.
        """
        for kline in self.klines:
            close_price = kline[4]  # Closing price of the candle
            if self.low <= close_price <= self.high:
                return False  # Zone is touched
        return True  # Zone is fresh

    @computed_field
    @property
    def mid_point(self) -> float:
        """
        Dynamically calculates the midpoint of the zone.

        Returns:
            float: The midpoint between the low and high of the zone.
        """
        return (self.low + self.high) / 2

    def __str__(self) -> str:
        """
        Provides a string representation of the Zone for debugging and display.

        Returns:
            str: String description of the Zone.
        """
        return (
            f"Zone(type={self.zone_type}, low={self.low}, high={self.high}, "
            f"creation_time={self.creation_time}, is_fresh={self.is_fresh})"
        )
