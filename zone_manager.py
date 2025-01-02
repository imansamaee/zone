from datetime import datetime
from pydantic import BaseModel

from models.zone import Zone

class ZoneManager:
    def __init__(self, klines, timeframe="support"):
        self.klines = klines
        self.timeframe = timeframe
        self.demand_zones = []
        self.supply_zones = []
        self.last_demand_zone = None
        self.last_supply_zone = None
        self.max_zones = 5  # Limit the number of zones stored
        self.update_zones(self.klines)

    def init(self):
        """Initializes the ZoneManager by creating zones."""
        try:
            (
                self.demand_zones,
                self.supply_zones,
            ) = ZoneManager.create_zones(
                self.klines, self.timeframe
            )
            
            # Limit the number of zones
            self.demand_zones = self.demand_zones[-self.max_zones:]
            self.supply_zones = self.supply_zones[-self.max_zones:]
        except Exception as e:
            print(f"Error initializing ZoneManager: {e}")

    def get_active_zones(self, price):
        """Returns a list of active zones (zones that the price is currently within)."""
        active_zones = []
        for zone in self.demand_zones + self.supply_zones:
            if zone.start_price <= price <= zone.end_price:
                active_zones.append(zone)
        return active_zones

    def update_zones(self, new_klines):
        """Updates the zones based on new Kline data."""
        self.klines = new_klines
        self.last_demand_zone = self.demand_zones[-1] if self.demand_zones else None
        self.last_supply_zone = self.supply_zones[-1] if self.supply_zones else None
        self.init()
        for zone in self.demand_zones + self.supply_zones:
            zone.update(self.klines)

    @staticmethod
    def create_zones(klines, timeframe="support"):
        """
        Creates supply and demand zones based on Kline data.

        Args:
            klines (list): List of Kline data.
            timeframe (str, optional): Timeframe of the Klines. Defaults to "support".

        Returns:
            tuple: A tuple containing lists of demand zones and supply zones.
        """
        demand_zones = []
        supply_zones = []

        for i in range(2, len(klines) - 2):
            try:
                current_kline = klines[i]
                previous_kline = klines[i - 1]
                next_kline = klines[i + 1]

                start_time = current_kline[0]
                end_time = current_kline[0] + 60

                # Minimum candle size to filter out small, insignificant zones
                high = current_kline[2]
                low = current_kline[3]
                close = current_kline[4]
                open_ = current_kline[1]
                candle_size = abs(close - open_)

                if candle_size < (high - low) * 0.3:  # Filter small candles
                    continue

                # Identify potential demand zones (swing lows)
                if (
                    current_kline[3] < previous_kline[3]
                    and current_kline[3] < next_kline[3]
                ):
                    demand_zones.append(
                        Zone(
                            start_price=current_kline[3],
                            end_price=current_kline[3] * 1.01,
                            start_time=start_time,
                            end_time=end_time,
                            timeframe=timeframe,
                        )
                    )

                # Identify potential supply zones (swing highs)
                if (
                    current_kline[2] > previous_kline[2]
                    and current_kline[2] > next_kline[2]
                ):
                    supply_zones.append(
                        Zone(
                            start_price=current_kline[2] * 0.99,
                            end_price=current_kline[2],
                            start_time=start_time,
                            end_time=end_time,
                            timeframe=timeframe,
                        )
                    )
            except Exception as e:
                print(f"Error creating zones at index {i}: {e}")
                continue

        return demand_zones, supply_zones
