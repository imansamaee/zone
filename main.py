import asyncio
from flask import Flask, render_template, request, session, redirect, url_for
from flask_static_compress import FlaskStaticCompress  # For compressing static files
import os
from loguru import logger
from hypercorn.asyncio import serve
from hypercorn.config import Config
from app_config import AppConfig

# from routes.crypto_routes import crypto_blueprint
from bot import UpdateBot
from routes.general_routes import general_blueprint
from routes.auth_routes import auth_blueprint
from routes.home_routes import home_blueprint

from routes.crypto_routes import crypto_blueprint
from routes.order_routes import order_blueprint
from routes.chart_routes import chart_blueprint


# Set logger level
AppConfig.set_logger("INFO")
AppConfig.rename_pairs_history_folder()

app = Flask(__name__, template_folder="templates")  # Add template_folder here
bot_initialization_lock = asyncio.Lock()
app.config['TEMPLATES_AUTO_RELOAD'] = True 


# Register blueprints
app.register_blueprint(general_blueprint)
app.register_blueprint(auth_blueprint, url_prefix="/auth")
app.register_blueprint(home_blueprint, url_prefix="/home")
app.register_blueprint(crypto_blueprint, url_prefix="/crypto")
app.register_blueprint(order_blueprint, url_prefix="/order")
app.register_blueprint(chart_blueprint, url_prefix="/chart")

# Configure static files and templates
app.static_folder = "static"
app.config["SECRET_KEY"] = "gdfsgsdhfrt44353DFDGS323#@#43"


async def run_app():
    config = Config()
    config.bind = [
        "0.0.0.0:" + str(AppConfig.port)
    ]  # Replace with your desired host and port
    config.use_reloader = True  # Enable reloader
    # allow to change html 

    # config.certfile = '/etc/letsencrypt/live/y.imansamaee.com/fullchain.pem'
    # config.keyfile = '/etc/letsencrypt/live/y.imansamaee.com/privkey.pem'

    await serve(app, config)  # Run the Flask app using Hypercorn


async def initialize_bot():
    """Initialize the bot and start updaters."""
    if not AppConfig.run_bot:
        return
    async with bot_initialization_lock:
        if not AppConfig.bot:
            try:
                update_bot = UpdateBot()
                AppConfig.bot = update_bot.bot
                AppConfig.add_task(asyncio.create_task(update_bot.start_updaters()))
            except Exception as e:
                logger.error(f"Error initializing bot: {e}")
                raise


async def run_all_tasks():
    """Run all tasks stored in AppConfig."""
    await asyncio.gather(*AppConfig.tasks)


async def main():
    """
    Main function to initialize and run all tasks.
    Ensures the bot and FastAPI server are started and managed centrally.
    """
    await AppConfig.kill_process_on_port(AppConfig.port)

    try:
        await initialize_bot()
        await run_app()
        await run_all_tasks()
    except asyncio.CancelledError:
        logger.info("Shutdown initiated. Cancelling tasks...")
    except Exception as e:
        logger.exception(f"Unexpected error in main: {e}")
    finally:
        await AppConfig.cancel_tasks()


if __name__ == "__main__":
    AppConfig.clear_terminal()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        AppConfig.is_shutdown_initiated = True
        logger.info("Shutdown initiated by user.")
    except Exception as e:
        logger.exception(f"An unexpected error occurred: {e}")
    finally:
        logger.info("Application shutdown complete.")
