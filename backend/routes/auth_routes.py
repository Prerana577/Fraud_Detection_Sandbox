"""
routes/auth_routes.py — Session-based authentication endpoints.

Endpoints:
  POST /api/auth/login   — Authenticate and start a session
  POST /api/auth/logout  — Destroy the current session
  GET  /api/auth/me      — Return current session identity
"""
import auth  # import the module, not symbols, to avoid name collision

from flask import Blueprint, request, jsonify, session

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate with username + password and create a session."""
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", "")).strip()

    result = auth.login(username, password)
    if result is None:
        return jsonify({"error": "Invalid username or password"}), 401

    session["username"] = result["username"]
    session["role"] = result["role"]
    return jsonify({"success": True, "role": result["role"]})


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Destroy the current session."""
    session.clear()
    return jsonify({"success": True})


@auth_bp.route("/me", methods=["GET"])
def me():
    """Return the currently authenticated user's identity."""
    return jsonify({
        "username": session.get("username", "guest"),
        "role": session.get("role", "guest"),
    })
