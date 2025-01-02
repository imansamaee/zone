import os
import re
from flask import Blueprint, redirect, render_template, request, session, url_for
from loguru import logger

from app_config import AppConfig

chart_blueprint = Blueprint('charts', __name__)


@chart_blueprint.route("/chart")
def crypto_chart():
    """Serves the crypto_chart.html template with details for the given symbol."""
    try:
        symbol = request.args.get('symbol')
        if not symbol:
            return "Missing symbol parameter", 400


        if 'username' not in session:
            return redirect(url_for('auth.login'))

        crypto_details = AppConfig.get_crypto(symbol)
        if not crypto_details:
            return "Crypto symbol not found", 404

        return render_template("crypto_chart.html", symbol=symbol, crypto=crypto_details.dict())

    except Exception as e:
        logger.error(f"Error getting crypto_chart.html: {e}")
        return "Error getting chart template.", 500