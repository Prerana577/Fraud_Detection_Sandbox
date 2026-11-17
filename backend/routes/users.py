"""
routes/users.py — User management endpoints.

Endpoints:
  GET  /api/users                    List all users
  POST /api/users/<id>/freeze        Freeze a user account
  POST /api/users/<id>/unfreeze      Unfreeze a user account
"""
import logging
from flask import Blueprint, jsonify, request
from models import db, User, Transaction
from sqlalchemy import func

logger = logging.getLogger(__name__)
users_bp = Blueprint("users", __name__, url_prefix="/api")


@users_bp.route("/users", methods=["GET"])
def list_users():
    """Return all users with optional search/filter."""
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()

    q = User.query
    if search:
        q = q.filter((User.name.ilike(f"%{search}%")) | (User.user_id.ilike(f"%{search}%")))
    if status:
        q = q.filter(User.status == status)

    users = q.order_by(User.name).all()
    result = []
    for u in users:
        d = u.to_dict()
        # Append quick stats
        d["total_txns"]   = Transaction.query.filter_by(user_id=u.user_id).count()
        d["blocked_txns"] = Transaction.query.filter_by(
            user_id=u.user_id, decision="BLOCK"
        ).count()
        result.append(d)

    return jsonify(result)


@users_bp.route("/users/<user_id>/freeze", methods=["POST"])
def freeze_user(user_id: str):
    """Freeze a user account (admin action)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.status = "frozen"
    db.session.commit()
    logger.info("[admin] User %s (%s) frozen manually.", user_id, user.name)
    return jsonify(user.to_dict())


@users_bp.route("/users/<user_id>/unfreeze", methods=["POST"])
def unfreeze_user(user_id: str):
    """Unfreeze a user account (admin action)."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    user.status = "active"
    db.session.commit()
    logger.info("[admin] User %s (%s) unfrozen manually.", user_id, user.name)
    return jsonify(user.to_dict())
