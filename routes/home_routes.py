import os
from flask import Blueprint, jsonify, redirect, render_template, session, url_for
from loguru import logger

from app_config import AppConfig, TradingStrategy

home_blueprint = Blueprint('home', __name__)

@home_blueprint.route('/crypto_volatility_html')
def get_crypto_volatility_html():
    if 'username' not in session:  # Check if the user is logged in
        return "Not authenticated", 401  # Return 401 Unauthorized if not logged in

    try:
        crypto_data = []
        for crypto in AppConfig.bot.products.cryptos.values():
            crypto_data.append(
                {
                    "symbol": crypto.symbol,
                    "volatility_factor_1m": crypto.volatility_factor_1m,
                    "volatility_factor_cover": crypto.volatility_factor_cover,
                    "next_support": crypto.next_support_resistance[0],
                    "current_price": crypto.current_price,
                    "next_resistance": crypto.next_support_resistance[1],
                    "sr_gap_pct": crypto.support_resistance_range_pct,
                    "lowest_support_1m": crypto.lowest_support_1m
                }
            )

        return render_template("crypto_volatility.html", cryptos=crypto_data)

    except Exception as e:
        logger.error(f"Error fetching test results: {e}")
        return "Error fetching test results", 500

@home_blueprint.route("/test_results_html")
def get_test_results_html():
    if 'username' not in session:
        return "Not authenticated", 401

    try:
        crypto_data = []
        for crypto in AppConfig.bot.products.cryptos.values():
            if hasattr(crypto, "test_results"):
                crypto_data.append({"symbol": crypto.symbol, "test_results": crypto.test_results})

        return render_template("test_results.html", cryptos=crypto_data)

    except Exception as e:
        logger.error(f"Error fetching test results: {e}")
        return "Error fetching test results", 500


@home_blueprint.route("/pnl_summary_html")
def pnl_summary():
    """
    Calculates and displays the PNL summary.
    """
    try:
        if 'username' not in session:
            return redirect(url_for('auth.login'))

        pairs_dir = "static/pairs_history"
        if not os.path.exists(pairs_dir):
            return "pairs_history directory not found", 404

        files = sorted(
            [f for f in os.listdir(pairs_dir) if f.endswith(".json")],
            key=lambda f: os.path.getmtime(os.path.join(pairs_dir, f)),
            reverse=True
        )

        return render_template("pnl_summary.html", files=files)

    except Exception as e:
        logger.error(f"Error calculating PNL summary: {e}")
        return f"Error calculating PNL summary: {e}", 500  # Return the error message with a 500 status code


@home_blueprint.route('/config_html')
def get_config_html():
    if 'username' in session:
        return render_template('config.html', AppConfig=AppConfig, TradingStrategy=TradingStrategy)
    else:
        return jsonify({'message': 'Please log in first'}), 401

