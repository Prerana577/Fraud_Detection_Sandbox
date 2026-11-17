"""
routes/config_routes.py — Runtime rule-threshold configuration.

Endpoints:
  GET /api/config    — Return current rule thresholds
  PUT /api/config    — Update one or more rule thresholds (hot-reload)

Changes are stored in app.config["RULE_CONFIG"] and take effect immediately
for all subsequent transactions — no restart required.
"""
import logging
from flask import Blueprint, jsonify, request, current_app

logger = logging.getLogger(__name__)
config_bp = Blueprint("config", __name__, url_prefix="/api")


@config_bp.route("/config", methods=["GET"])
def get_config():
    """Return the current rule configuration."""
    return jsonify(current_app.config["RULE_CONFIG"])


@config_bp.route("/config", methods=["PUT"])
def update_config():
    """
    Merge the request body into the existing RULE_CONFIG.
    Accepts partial updates — only specified keys are changed.

    Example body:
    {
      "impossible_travel": {"speed_threshold_kmh": 700},
      "velocity": {"max_txns": 3}
    }
    """
    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400

    cfg = current_app.config["RULE_CONFIG"]
    valid_rules = set(cfg.keys())

    for rule_name, updates in data.items():
        if rule_name not in valid_rules:
            return jsonify({
                "error": f"Unknown rule '{rule_name}'. "
                         f"Valid rules: {sorted(valid_rules)}"
            }), 422
        if not isinstance(updates, dict):
            return jsonify({"error": f"Updates for '{rule_name}' must be an object"}), 422
        # Deep-merge: only update provided keys
        cfg[rule_name].update(updates)
        logger.info("[config] Updated rule '%s': %s", rule_name, updates)

    return jsonify(cfg)
