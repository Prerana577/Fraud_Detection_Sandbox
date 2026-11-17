"""
routes/notify_routes.py — Notification log endpoints.

Endpoints:
  GET    /api/notify/log   — Retrieve notification log
  DELETE /api/notify/log   — Clear notification log
  POST   /api/notify/test  — Send a test notification for a user
"""
from flask import Blueprint, request, jsonify

from notifications import notification_service
from models import User, db

notify_bp = Blueprint("notify", __name__, url_prefix="/api/notify")


@notify_bp.route("/log", methods=["GET"])
def get_log():
    """Return the in-memory notification log."""
    return jsonify({"log": notification_service.get_log()})


@notify_bp.route("/log", methods=["DELETE"])
def clear_log():
    """Clear the in-memory notification log."""
    notification_service.clear_log()
    return jsonify({"cleared": True})


@notify_bp.route("/test", methods=["POST"])
def send_test():
    """
    Send a test notification for a given user.

    JSON body:
      { "type": "fraud_alert" | "account_frozen" | "otp_challenge", "user_id": "<uuid>" }
    """
    data = request.get_json(silent=True) or {}
    notify_type = str(data.get("type", "")).strip()
    user_id = str(data.get("user_id", "")).strip()

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": f"User '{user_id}' not found"}), 404

    if notify_type == "fraud_alert":
        entry = notification_service.send_fraud_alert(
            user_name=user.name,
            txn_id="test-txn-0000",
            decision="FLAG",
            amount=9999.0,
            city=user.home_city,
            risk_score=85,
        )
    elif notify_type == "account_frozen":
        entry = notification_service.send_account_frozen(
            user_name=user.name,
            user_id=user.user_id,
        )
    elif notify_type == "otp_challenge":
        entry = notification_service.send_otp_challenge(
            user_name=user.name,
            user_id=user.user_id,
            txn_id="test-txn-0000",
        )
    else:
        return jsonify({"error": f"Unknown notification type '{notify_type}'. Use fraud_alert, account_frozen, or otp_challenge."}), 400

    return jsonify(entry), 200
