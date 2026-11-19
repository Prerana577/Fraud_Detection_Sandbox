"""
app.py — Flask application factory for the Fraud Detection Sandbox.

Usage:
    python app.py                  # development server
    flask run --port 5001          # alternate

The factory pattern (create_app) makes the app easy to test and avoids
circular import issues between models, routes, and the simulator.
"""
import logging
import os

from flask import Flask, jsonify
from flask_socketio import SocketIO
from flask_cors import CORS

from config import Config
from models import db
import redis_store

# Module-level SocketIO instance (imported by routes that need to emit events)
socketio = SocketIO()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def create_app(config_class=Config) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.secret_key = app.config.get("SECRET_KEY", "fraud-detection-secret-key")

    # ── Extensions ────────────────────────────────────────────────────────────
    db.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # SocketIO with eventlet async mode; falls back gracefully
    socketio.init_app(
        app,
        cors_allowed_origins="*",
        async_mode="threading",   # works without eventlet installed
        logger=False,
        engineio_logger=False,
    )
    # Expose socketio on app.extensions so routes can access it
    app.extensions["socketio"] = socketio

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_store.init_redis(app.config.get("REDIS_URL", ""))

    # ── Blueprints ────────────────────────────────────────────────────────────
    from routes.transactions   import txn_bp,    process_transaction
    from routes.stats          import stats_bp
    from routes.users          import users_bp
    from routes.config_routes  import config_bp
    from routes.simulator_routes import sim_bp
    from routes.ml_routes      import ml_bp
    from routes.export_routes  import export_bp
    from routes.notify_routes  import notify_bp
    from routes.replay_routes  import replay_bp
    from routes.auth_routes    import auth_bp
    from routes.backtest_routes import backtest_bp

    app.register_blueprint(txn_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(sim_bp)
    app.register_blueprint(ml_bp)
    app.register_blueprint(export_bp)
    app.register_blueprint(notify_bp)
    app.register_blueprint(replay_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(backtest_bp)

    # ── Database + seed ───────────────────────────────────────────────────────
    with app.app_context():
        db.create_all()
        if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
            try:
                db.session.execute(db.text("PRAGMA journal_mode=WAL;"))
                db.session.execute(db.text("PRAGMA synchronous=NORMAL;"))
                db.session.commit()
            except Exception as exc:
                logger.debug("[db] WAL mode setup note: %s", exc)
        _auto_seed(app)

    # ── Simulator wiring ──────────────────────────────────────────────────────
    from simulator import simulator

    def _process_fn(data: dict):
        """Wrap process_transaction so the simulator runs inside app context."""
        with app.app_context():
            try:
                process_transaction(data, socketio=socketio)
            except Exception as exc:
                logger.error("[simulator._process_fn] %s", exc, exc_info=True)

    simulator.configure(
        app=app,
        socketio=socketio,
        process_fn=_process_fn,
        min_delay=app.config["SIMULATOR_MIN_DELAY"],
        max_delay=app.config["SIMULATOR_MAX_DELAY"],
    )

    # ── Health check ──────────────────────────────────────────────────────────
    @app.route("/api/health")
    def health():
        return jsonify({
            "status": "ok",
            "db":     app.config["SQLALCHEMY_DATABASE_URI"].split("://")[0],
            "redis":  redis_store.is_redis_available(),
        })

    # ── WebSocket events ──────────────────────────────────────────────────────
    @socketio.on("connect")
    def on_connect():
        logger.info("[ws] Client connected.")

    @socketio.on("disconnect")
    def on_disconnect():
        logger.info("[ws] Client disconnected.")

    # Periodically push stats update every 5 seconds to all clients
    @socketio.on("request_stats")
    def on_request_stats():
        from routes.stats import get_stats
        with app.app_context():
            resp = get_stats()
            socketio.emit("stats_update", resp.get_json())

    return app


def _auto_seed(app: Flask):
    """Seed the database if no users exist yet."""
    from models import User
    if User.query.count() == 0:
        logger.info("[app] No users found — running seed data…")
        try:
            from seed import seed_users
            seed_users()
        except Exception as exc:
            logger.error("[app] Seed failed: %s", exc, exc_info=True)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", 5001))
    logger.info("Starting Fraud Detection Sandbox on http://0.0.0.0:%d", port)
    socketio.run(app, host="0.0.0.0", port=port, debug=app.config["DEBUG"],
                 use_reloader=False, allow_unsafe_werkzeug=True)
