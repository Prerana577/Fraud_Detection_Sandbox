"""
routes/simulator_routes.py — Simulator control endpoints.

Endpoints:
  POST /api/simulator/start    — Start simulation
  POST /api/simulator/stop     — Stop simulation
  PUT  /api/simulator/speed    — Set delay range
  POST /api/simulator/inject   — Inject a specific fraud pattern
  GET  /api/simulator/status   — Return running state + settings
"""
import logging
from flask import Blueprint, jsonify, request

logger = logging.getLogger(__name__)
sim_bp = Blueprint("simulator", __name__, url_prefix="/api/simulator")


def _get_sim():
    """Lazily import the simulator singleton to avoid circular imports."""
    from simulator import simulator
    return simulator


@sim_bp.route("/start", methods=["POST"])
def start_simulator():
    return jsonify(_get_sim().start())


@sim_bp.route("/stop", methods=["POST"])
def stop_simulator():
    return jsonify(_get_sim().stop())


@sim_bp.route("/speed", methods=["PUT"])
def set_speed():
    data      = request.get_json(silent=True) or {}
    min_delay = float(data.get("min_delay", 0.5))
    max_delay = float(data.get("max_delay", 2.0))
    if min_delay <= 0 or max_delay < min_delay:
        return jsonify({"error": "Invalid delay values — min_delay > 0 and max_delay >= min_delay"}), 422
    return jsonify(_get_sim().set_speed(min_delay, max_delay))


@sim_bp.route("/inject", methods=["POST"])
def inject_pattern():
    data    = request.get_json(silent=True) or {}
    pattern = str(data.get("pattern", ""))
    user_id = data.get("user_id")
    valid   = {"impossible_travel", "velocity_burst", "large_amount", "repeated_failures"}
    if pattern not in valid:
        return jsonify({"error": f"pattern must be one of {sorted(valid)}"}), 422
    result = _get_sim().inject(pattern, user_id)
    return jsonify(result)


@sim_bp.route("/status", methods=["GET"])
def simulator_status():
    sim = _get_sim()
    return jsonify({
        "running":   sim.is_running(),
        "min_delay": sim.min_delay,
        "max_delay": sim.max_delay,
    })


@sim_bp.route("/alerts", methods=["GET"])
def list_alerts():
    """Return recent alerts (most recent 50)."""
    from models import Alert
    alerts = Alert.query.order_by(Alert.created_at.desc()).limit(50).all()
    return jsonify([a.to_dict() for a in alerts])


@sim_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id: int):
    """Mark an alert as acknowledged."""
    from models import db, Alert
    alert = Alert.query.get(alert_id)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
    alert.acknowledged = True
    db.session.commit()
    return jsonify(alert.to_dict())
