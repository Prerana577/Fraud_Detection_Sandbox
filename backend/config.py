"""
config.py — Central configuration for the Fraud Detection Sandbox.

All settings are read from environment variables (populated via .env).
Sensible defaults ensure the app runs out-of-the-box even without Docker.
"""
import os
from dotenv import load_dotenv

# Load .env from the project root (one level up from backend/)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))
# Also try a local .env in case the user created one inside backend/
load_dotenv(override=False)


class Config:
    # ── Flask ─────────────────────────────────────────────────────────────────
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-not-for-prod")
    DEBUG: bool = os.getenv("FLASK_DEBUG", "1") == "1"

    # ── Database ──────────────────────────────────────────────────────────────
    # Prefer Postgres if DATABASE_URL is set, else fall back to local SQLite.
    _db_url = os.getenv("DATABASE_URL", "")
    SQLALCHEMY_DATABASE_URI: str = (
        _db_url if _db_url
        else f"sqlite:///{os.path.join(os.path.dirname(__file__), 'fraud.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "connect_args": {"timeout": 30}
    } if "sqlite" in SQLALCHEMY_DATABASE_URI else {}

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = os.getenv("REDIS_URL", "")  # empty = use in-memory fallback

    # ── Fraud Rules (can be overridden at runtime via /api/config) ─────────────
    RULE_CONFIG: dict = {
        "impossible_travel": {
            "speed_threshold_kmh": 900,   # if implied speed > this → fraud
            "points": 50,
        },
        "velocity": {
            "max_txns": 5,                # more than this many txns …
            "window_seconds": 120,        # … within this window → fraud
            "points": 30,
        },
        "amount_anomaly": {
            "multiplier": 3.0,            # amount > multiplier × avg_amount
            "zscore_threshold": 3.0,      # OR z-score > this
            "points": 25,
        },
        "repeated_failures": {
            "min_failures": 3,            # ≥ this many failed txns …
            "window_seconds": 600,        # … within this window → fraud + freeze
            "points": 30,
        },
    }

    # Decision thresholds (sum of rule points → decision label)
    SCORE_APPROVE_MAX: int = 39   # 0-39  → APPROVE
    SCORE_FLAG_MAX: int = 69      # 40-69 → FLAG
    # 70-100 → BLOCK

    # ── Simulator defaults ────────────────────────────────────────────────────
    SIMULATOR_MIN_DELAY: float = float(os.getenv("SIMULATOR_MIN_DELAY", "0.5"))
    SIMULATOR_MAX_DELAY: float = float(os.getenv("SIMULATOR_MAX_DELAY", "2.0"))
    FRAUD_INJECT_RATE: float = float(os.getenv("FRAUD_INJECT_RATE", "0.1"))

    # Redis key TTL (seconds) — recent activity expires after 15 minutes
    REDIS_TTL: int = 900
