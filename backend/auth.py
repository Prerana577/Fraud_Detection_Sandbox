from functools import wraps
from flask import session, jsonify

USERS_DB = {
    "admin":   {"password": "admin123",   "role": "admin"},
    "analyst": {"password": "analyst123", "role": "analyst"},
}


def login(username, password):
    u = USERS_DB.get(username)
    return {"username": username, "role": u["role"]} if u and u["password"] == password else None


def get_role(session_dict):
    return session_dict.get("role", "guest")


def require_role(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") not in roles:
                return jsonify({"error": "Forbidden", "required": list(roles)}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator
