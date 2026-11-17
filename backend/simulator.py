"""
simulator.py — Background transaction generator for the Fraud Detection Sandbox.

Generates realistic transactions every 0.5–2 seconds (adjustable).
About 90% are "normal" behaviour; ~10% inject one of four fraud patterns:
  • impossible_travel  — transaction far from home city
  • velocity_burst     — 8 rapid transactions in quick succession
  • large_amount       — amount = 8× user's average
  • repeated_failures  — 4 consecutive failed transactions

The simulator runs in a daemon thread and calls the same scoring pipeline
that the REST API uses, ensuring perfect parity.
"""
import random
import time
import threading
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ─── Indian city pool for "away" fraud locations ──────────────────────────────
_FRAUD_CITIES = [
    {"city": "Guwahati",   "lat": 26.1445, "lon": 91.7362},
    {"city": "Kolkata",    "lat": 22.5726, "lon": 88.3639},
    {"city": "Delhi",      "lat": 28.6139, "lon": 77.2090},
    {"city": "Mumbai",     "lat": 19.0760, "lon": 72.8777},
    {"city": "Chennai",    "lat": 13.0827, "lon": 80.2707},
    {"city": "Bengaluru",  "lat": 12.9716, "lon": 77.5946},
    {"city": "Hyderabad",  "lat": 17.3850, "lon": 78.4867},
    {"city": "Ahmedabad",  "lat": 23.0225, "lon": 72.5714},
]

# Merchant names per category (for realistic data)
_MERCHANTS = [
    "Swiggy", "Zomato", "Amazon.in", "Flipkart", "BigBasket",
    "Nykaa", "Myntra", "BookMyShow", "Ola", "Uber",
    "IRCTC", "MakeMyTrip", "Paytm Mall", "PhonePe Store", "Zepto",
    "Blinkit", "Dunzo", "Decathlon India", "Croma", "Reliance Digital",
]


class TransactionSimulator:
    """
    Thread-safe simulator that generates transactions and pushes them through
    the scoring pipeline + WebSocket broadcast.
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._lock = threading.Lock()
        self.min_delay: float = 0.5
        self.max_delay: float = 2.0
        # Will be injected by app factory to avoid circular imports
        self._app = None
        self._socketio = None
        self._process_fn = None   # callable(txn_data) → Transaction

    def configure(self, app, socketio, process_fn, min_delay=0.5, max_delay=2.0):
        """Called once from the app factory to wire up dependencies."""
        self._app = app
        self._socketio = socketio
        self._process_fn = process_fn
        self.min_delay = min_delay
        self.max_delay = max_delay

    # ── Public control methods ────────────────────────────────────────────────

    def start(self):
        """Start the simulation thread (idempotent)."""
        if self._running.is_set():
            return {"status": "already_running"}
        self._running.set()
        self._thread = threading.Thread(target=self._run, daemon=True, name="simulator")
        self._thread.start()
        logger.info("[simulator] Started.")
        return {"status": "started"}

    def stop(self):
        """Signal the simulation thread to stop."""
        self._running.clear()
        logger.info("[simulator] Stopped.")
        return {"status": "stopped"}

    def set_speed(self, min_delay: float, max_delay: float):
        """Adjust the transaction generation rate."""
        with self._lock:
            self.min_delay = max(0.1, min_delay)
            self.max_delay = max(self.min_delay, max_delay)
        return {"min_delay": self.min_delay, "max_delay": self.max_delay}

    def inject(self, pattern: str, user_id: str | None = None):
        """
        Immediately inject one fraud pattern into the pipeline.
        pattern: "impossible_travel" | "velocity_burst" | "large_amount" | "repeated_failures"
        """
        if self._process_fn is None:
            return {"error": "Simulator not configured yet"}
        with self._app.app_context():
            return self._inject_pattern(pattern, user_id)

    def is_running(self) -> bool:
        return self._running.is_set()

    # ── Internal thread loop ──────────────────────────────────────────────────

    def _run(self):
        """Main simulation loop — runs until stop() is called."""
        with self._app.app_context():
            while self._running.is_set():
                try:
                    self._generate_one()
                except Exception as exc:
                    logger.error("[simulator] Error generating transaction: %s", exc, exc_info=True)
                with self._lock:
                    delay = random.uniform(self.min_delay, self.max_delay)
                time.sleep(delay)

    def _generate_one(self):
        """Generate one transaction — 90% normal, 10% fraudulent."""
        from models import User
        # Pick a random active-ish user
        users = User.query.filter(User.status != "deleted").all()
        if not users:
            return
        user = random.choice(users)

        fraud_roll = random.random()
        if fraud_roll < 0.10:
            pattern = random.choice(
                ["impossible_travel", "velocity_burst", "large_amount", "repeated_failures"]
            )
            self._inject_pattern(pattern, user.user_id)
        else:
            self._normal_transaction(user)

    def _normal_transaction(self, user):
        """Generate a normal transaction near the user's home city."""
        # Add small lat/lon jitter (within ~30 km)
        lat = user.home_lat + random.uniform(-0.3, 0.3)
        lon = user.home_lon + random.uniform(-0.3, 0.3)
        amount = user.avg_amount * random.uniform(0.4, 1.6)
        self._submit({
            "user_id":    user.user_id,
            "amount":     round(amount, 2),
            "merchant":   random.choice(_MERCHANTS),
            "city":       user.home_city,
            "lat":        round(lat, 4),
            "lon":        round(lon, 4),
            "txn_status": "success",
        })

    def _inject_pattern(self, pattern: str, user_id: str | None):
        """Inject a specific fraud pattern."""
        from models import User, db
        if user_id:
            user = User.query.get(user_id)
        else:
            users = User.query.all()
            user = random.choice(users) if users else None
        if not user:
            return {"error": "No user found"}

        if pattern == "impossible_travel":
            # Pick a city far from user's home
            far_city = random.choice([
                c for c in _FRAUD_CITIES if c["city"] != user.home_city
            ])
            self._submit({
                "user_id":  user.user_id,
                "amount":   round(user.avg_amount * random.uniform(0.8, 1.4), 2),
                "merchant": random.choice(_MERCHANTS),
                "city":     far_city["city"],
                "lat":      far_city["lat"],
                "lon":      far_city["lon"],
                "txn_status": "success",
            })

        elif pattern == "velocity_burst":
            # 8 rapid transactions (no sleep — all submitted synchronously)
            for _ in range(8):
                lat = user.home_lat + random.uniform(-0.1, 0.1)
                lon = user.home_lon + random.uniform(-0.1, 0.1)
                self._submit({
                    "user_id":  user.user_id,
                    "amount":   round(user.avg_amount * random.uniform(0.5, 1.2), 2),
                    "merchant": random.choice(_MERCHANTS),
                    "city":     user.home_city,
                    "lat":      round(lat, 4),
                    "lon":      round(lon, 4),
                    "txn_status": "success",
                })

        elif pattern == "large_amount":
            self._submit({
                "user_id":  user.user_id,
                "amount":   round(user.avg_amount * 8, 2),   # 8× average
                "merchant": random.choice(_MERCHANTS),
                "city":     user.home_city,
                "lat":      user.home_lat,
                "lon":      user.home_lon,
                "txn_status": "success",
            })

        elif pattern == "repeated_failures":
            for _ in range(4):
                self._submit({
                    "user_id":  user.user_id,
                    "amount":   round(user.avg_amount * 0.9, 2),
                    "merchant": random.choice(_MERCHANTS),
                    "city":     user.home_city,
                    "lat":      user.home_lat,
                    "lon":      user.home_lon,
                    "txn_status": "failed",
                })

        return {"injected": pattern, "user_id": user.user_id}

    def _submit(self, data: dict):
        """Push transaction data through the same processing pipeline as POST /api/transaction."""
        if self._process_fn:
            self._process_fn(data)


# Module-level singleton
simulator = TransactionSimulator()
