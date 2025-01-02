from datetime import datetime
from pydantic import BaseModel

class Zone(BaseModel):
    start_price: float
    end_price: float
    start_time: int
    end_time: int
    strength: float = 1.0
    is_tested: bool = False
    tested_at: datetime = None
    breakout_direction: str = None
    false_breakout_count: int = 0
    formation_time: datetime = datetime.now()
    timeframe: str = None
    volume_profile: list = []
    order_flow_imbalance: float = 0.0

    def update(self, klines, price=None, direction=None):
        """Updates the zone's strength and tests for breakouts."""
        self.calculate_strength(klines)
        if price is not None and direction is not None:
            self.test_zone(price, direction)

    def test_zone(self, price, direction):
        """Tests if the zone is broken."""
        self.is_tested = True
        self.tested_at = datetime.now()

        if direction == "up" and price > self.end_price:
            self.breakout_direction = "up"
        elif direction == "down" and price < self.start_price:
            self.breakout_direction = "down"
        else:
            self.false_breakout_count += 1

    def calculate_strength(self, klines):
        """Calculates the strength of the zone."""
        touches = 0
        total_volume = 0
        candle_size_score = 0

        if not klines:
            print("Klines list is empty. Cannot calculate strength.")
            return

        for kline in klines:
            try:
                high = float(kline[2])
                low = float(kline[3])
                close = float(kline[4])
                open_ = float(kline[1])
                volume = float(kline[5])

                # Candle size evaluation
                candle_size = abs(close - open_)
                if candle_size > (high - low) * 0.7:  # Large candle body
                    candle_size_score += 1

                if (
                    self.start_price <= high <= self.end_price
                    or self.start_price <= low <= self.end_price
                ):
                    touches += 1
                    total_volume += volume
            except Exception as e:
                print(f"Error processing Kline data: {e}")
                continue

        try:
            self.strength = (touches * total_volume * candle_size_score) / (
                len(klines) * (self.end_price - self.start_price)
            )
        except ZeroDivisionError:
            print("ZeroDivisionError in calculate_strength. Check zone price range.")

    def is_fresh(self):
        """Checks if the zone is fresh and untested."""
        return not self.is_tested

    def has_valid_risk_to_reward(self, entry_price, target_price, stop_loss):
        """Checks if the trade offers a valid risk-to-reward ratio."""
        risk = abs(entry_price - stop_loss)
        reward = abs(target_price - entry_price)
        return reward / risk >= 3
