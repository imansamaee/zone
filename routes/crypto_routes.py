from http.client import HTTPException
from flask import Blueprint, jsonify, redirect, session, url_for
from loguru import logger

from app_config import AppConfig

crypto_blueprint = Blueprint("crypto", __name__)

@crypto_blueprint.route("/symbol/<string:symbol>")
def get_crypto_by_symbol(symbol):
    """
    Fetch crypto data for a specific symbol, excluding klines_1m and klines_cover attributes.
    """
    try:

        crypto = AppConfig.get_crypto(symbol)
        if not crypto:
            raise HTTPException(status_code=404, detail=f"Crypto symbol {symbol} not found")

        # Exclude klines_1m and klines_cover from the crypto data
        crypto_data = {k: v for k, v in crypto.dict().items() if k not in ("klines_1m", "klines_cover")}

        return jsonify(crypto_data)

    except Exception as e:
        logger.error(f"Error fetching crypto data for symbol {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Error fetching crypto data")



@crypto_blueprint.route("/klines/<kline_type>/<symbol>")  # Updated route
def get_crypto_klines(kline_type, symbol):  # Added symbol parameter
    """
    Fetches the specified kline type (klines_1m or klines_cover) for the given symbol,
    including the crypto symbol.
    """
    if "username" not in session:
        return redirect(url_for('auth.login'))  # Redirect to login if not authenticated

    if kline_type not in ("1m", "cover"):
        raise HTTPException(status_code=400, detail="Invalid kline type")

    try:
        cryptos = AppConfig.bot.products.cryptos
        if not cryptos:
            raise HTTPException(status_code=404, detail="No cryptos found")

        crypto = AppConfig.get_crypto(symbol)
        if not crypto:
            raise HTTPException(status_code=404, detail=f"Crypto '{symbol}' not found")

        klines_data = getattr(crypto, f"klines_{kline_type}")
        return jsonify(klines_data)

    except Exception as e:
        logger.error(f"Error fetching klines data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching klines data")