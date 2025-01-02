from typing import List, Optional

from models.crypto import Crypto
from pydantic import BaseModel, Field, computed_field
from app_config import AppConfig

class CryptoTag(BaseModel):
    tag: str

    def get_cryptos(self) -> List["Crypto"]:  # Changed to a regular method
        """
        Returns the list of cryptos associated with this tag.
        """
        all_cryptos = AppConfig.bot.products.cryptos
        return [crypto for crypto in all_cryptos.values() if self.tag in crypto.tags]

    @computed_field
    @property
    def bullish_pct(self) -> float:
        """Calculates the pct of cryptos in this tag that are bullish."""
        cryptos = self.get_cryptos()  # Call the get_cryptos method
        if not cryptos:
            return 0.0
        bullish_count = sum(1 for crypto in cryptos if crypto.is_bullish)
        return (bullish_count / len(cryptos)) * 100

    def add_crypto(self, crypto: "Crypto"):
        """
        This method is no longer needed since cryptos are now fetched dynamically.
        """
        pass 

    def average_price_change(self) -> float:
        """Calculate the average price change of cryptos in this tag."""
        valid_changes = [
            (crypto.current_price - crypto.opening_price) / crypto.opening_price * 100
            for crypto in self.cryptos if crypto.opening_price > 0
        ]
        if not valid_changes:  # If no valid price changes
            return 0.0
        return sum(valid_changes) / len(valid_changes)

    class Config:
        json_encoders = {
            "Crypto": lambda c: c.dict()  # Encode Crypto instances as dictionaries
        }