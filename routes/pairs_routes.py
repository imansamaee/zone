import os
import json
from flask import Blueprint, render_template, jsonify, session, redirect, url_for
from loguru import logger  # Make sure to install and import loguru

pairs_blueprint = Blueprint('pairs', __name__)


@pairs_blueprint.route("/chart")
def get_chart():
    """
    Serves the pairs_chart.html template.
    """
    try:
        if 'username' not in session:
            return redirect(url_for('auth.login'))  # Redirect to login if not authenticated
        return render_template("pairs_chart.html")

    except Exception as e:
        logger.error(f"Error getting pairs_chart.html: {e}")
        return "Error getting chart template.", 500

@pairs_blueprint.route("/pairs_history")
def get_pairs_history():
    """Returns a list of JSON files in the 'pairs_history' directory."""
    try:
        if 'username' not in session:
            return redirect(url_for('auth.login'))  # Redirect to login if not authenticated
        pairs_dir = "static/pairs_history"
        if not os.path.exists(pairs_dir):
            return jsonify({"error": "pairs_history directory not found"})

        files = [
            {"name": f, "mtime": os.path.getmtime(os.path.join(pairs_dir, f))}
            for f in os.listdir(pairs_dir)
            if f.endswith(".json")
        ]
        return jsonify(files)

    except Exception as e:
        logger.error(f"Error getting pairs history: {e}")
        return jsonify({"error": str(e)})



@pairs_blueprint.route("/trades_data")
def get_trades_data():
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
                            'crypto': data.get('crypto', {}),
                            'pnl': data.get('pnl'),
                        })
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping invalid JSON file: {filename}")

        return jsonify(pnl_data)

    except Exception as e:
        logger.error(f"Error fetching PNL data: {e}")
        return f"Error fetching PNL data: {e}", 500