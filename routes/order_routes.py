import json
import os
from flask import Blueprint, jsonify, redirect, session, url_for
from loguru import logger

from app_config import AppConfig

order_blueprint = Blueprint('orders', __name__)

@order_blueprint.route("/convert_assets", methods=["GET"])
def convert_assets_to_usdt():
    if 'username' not in session:  # Check if the user is logged in
        return "Not authenticated", 401  # Return 401 Unauthorized if not logged in
    try:
        AppConfig.bot.order_manager.convert_all_assets_to_usdt()
        return jsonify({"message": "Conversion initiated"})
    except Exception as e:
        return jsonify({"detail": f"Error converting assets: {e}"}), 500


@order_blueprint.route("/open_orders", methods=["GET"])
def get_open_orders():
    if 'username' not in session:
        return "Not authenticated", 401
    try:
        return jsonify(AppConfig.bot.order_manager.open_orders)
    except Exception as e:
        return jsonify({"detail": f"Error fetching open orders: {e}"}), 500


@order_blueprint.route("/order_history", methods=["GET"])
def get_order_history():
    if 'username' not in session:
        return "Not authenticated", 401
    try:
        return jsonify({
            order.id: order.original_dict
            for order in AppConfig.bot.order_manager.order_history
        })
    except Exception as e:
        return jsonify({"detail": "Error fetching order history data"}), 500


@order_blueprint.route("/pnl_per_symbol", methods=["GET"])
def get_pnl_per_symbol():
    if 'username' not in session:
        return "Not authenticated", 401 
    try:
        return jsonify(AppConfig.bot.order_manager.pnl_per_symbol)
    except Exception as e:
        return jsonify({"detail": "Error fetching PNL per symbol data"}), 500


@order_blueprint.route("/pnl_data", methods=["GET"])
def get_pnl_data():
    """
    Returns PNL data with authorization_time for each order.
    """
    try:
        if 'username' not in session:
            return redirect(url_for('auth.login'))  # Redirect to login if not authenticated
        pairs_dir = "static/pairs_history"
        if not os.path.exists(pairs_dir):
            return "pairs_history directory not found", 404

        pnl_data = []

        for filename in os.listdir(pairs_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(pairs_dir, filename)
                with open(filepath, 'r') as f:
                    try:
                        data = json.load(f)
                        pnl_data.append({
                            'symbol': data.get('crypto', {}).get('symbol'),
                            'authorization_time': data.get('authorization_time'),
                            'pnl': data.get('pnl'),
                            'fileName': filename,
                            'volatilityFactor1m': data.get('crypto', {}).get('volatility_factor_1m'),
                            'volatilityFactorcover': data.get('crypto', {}).get('volatility_factor_cover'),
                            'supportResistance1m': data.get('crypto', {}).get('support_resistance_1m'),

                        })
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON file: {filename}")

        return jsonify(pnl_data)

    except Exception as e:
        logger.error(f"Error fetching PNL data: {e}")
        return f"Error fetching PNL data: {e}", 500