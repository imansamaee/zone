import asyncio
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    session,
    send_from_directory,
    current_app,
)  # Import current_app
import os
import json
from loguru import logger
from app_config import AppConfig, TradingStrategy
from bot import UpdateBot


general_blueprint = Blueprint("general", __name__)


@general_blueprint.route("/")
def index():
    if "username" in session:
        return render_template("index.html", user=session["username"])
    else:
        return redirect(url_for("auth.login"))  # Redirect to login if not signed in


@general_blueprint.route("/start_bot", methods=["POST"])
def start_bot():
    """Starts the bot."""
    try:
        if "username" in session:
            asyncio.run(initialize_bot())
            return jsonify({"message": "Bot start initiated"})
        else:
            return jsonify({"message": "Please log in first"}), 401
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return jsonify({"message": "Error starting bot"}), 500


@general_blueprint.route("/stop_bot", methods=["POST"])
def stop_bot():
    """Stops the bot."""
    try:
        if "username" in session:
            # Your bot stopping logic here...
            return jsonify({"message": "Bot stop initiated"})
        else:
            return jsonify({"message": "Please log in first"}), 401
    except Exception as e:
        logger.error(f"Error stopping bot: {e}")
        return jsonify({"message": "Error stopping bot"}), 500


@general_blueprint.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(current_app.root_path, "static"),  # Use current_app.root_path
        "favicon.ico",
        mimetype="image/vnd.microsoft.icon",
    )


@general_blueprint.route("/get_config")
def get_config():
    if "username" in session:
        return jsonify(AppConfig.get_config_as_dict())
    else:
        return jsonify({"message": "Please log in first"}), 401


@general_blueprint.route("/update_config", methods=["POST"])
def update_config():
    if "username" in session:
        try:
            # Access form data directly (no need for request.json() in Flask)
            AppConfig.trading_strategy = TradingStrategy[
                request.form.get("trading_strategy")
            ]
            AppConfig.run_bot = request.form.get("run_bot") == "true"
            AppConfig.convert_assets = request.form.get("convert_assets") == "true"
            AppConfig.flash_pct = float(request.form.get("flash_pct"))
            AppConfig.volatility_factor = float(request.form.get("volatility_factor"))
            AppConfig.stability_factor = float(request.form.get("stability_factor"))
            AppConfig.KLINE_LIMIT = int(request.form.get("kline_limit"))

            # Handle potential missing values
            crypto_limit = request.form.get("crypto_limit")
            AppConfig.CRYPTO_LIMIT = (
                int(crypto_limit) if crypto_limit is not None else None
            )

            AppConfig.ORDER_USDT_AMOUNT = int(request.form.get("order_usdt_amount"))
            AppConfig.MAX_USDT_TO_PLACE = int(request.form.get("max_usdt_to_place"))
            AppConfig.volatility = json.loads(request.form.get("volatility"))
            AppConfig.min_sr_gap_pct = float(request.form.get("min_sr_gap_pct"))
            AppConfig.support_closeness_threshold_pct = float(
                request.form.get("support_closeness_threshold_pct")
            )
            AppConfig.resistance_closeness_threshold_pct = float(
                request.form.get("resistance_closeness_threshold_pct")
            )
            AppConfig.check_buy_order_wait = int(
                request.form.get("check_buy_order_wait")
            )
            AppConfig.check_sell_order_wait = int(
                request.form.get("check_sell_order_wait")
            )
            AppConfig.price_updater_interval = int(
                request.form.get("price_updater_interval")
            )
            AppConfig.check_and_create_orders_interval = int(
                request.form.get("check_and_create_orders_interval")
            )
            AppConfig.monitor_orders_interval = int(
                request.form.get("monitor_orders_interval")
            )
            AppConfig.updating_klines_interval = int(
                request.form.get("updating_klines_interval")
            )
            AppConfig.stop_loss_pct = float(request.form.get("stop_loss_pct"))
            AppConfig.binance_cost_pct = float(request.form.get("binance_cost_pct"))
            AppConfig.blacklist = request.form.getlist(
                "blacklist"
            )  # Get multiple values if it's a list

            return jsonify({"message": "Configuration updated successfully"})

        except Exception as e:
            logger.error(f"Error updating configuration: {e}")
            return jsonify({"message": "Error updating configuration"}), 500
    else:
        return jsonify({"message": "Please log in first"}), 401


async def initialize_bot():
    """Initialize the bot and start updaters."""
    if not AppConfig.run_bot:
        return
    bot_initialization_lock = asyncio.Lock()
    async with bot_initialization_lock:
        if not AppConfig.bot:
            try:
                update_bot = UpdateBot()
                AppConfig.bot = update_bot.bot
                AppConfig.add_task(asyncio.create_task(update_bot.start_updaters()))
            except Exception as e:
                logger.error(f"Error initializing bot: {e}")
                raise
