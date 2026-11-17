"""
redis_store.py — Thin wrapper around Redis for per-user activity tracking.

If Redis is unavailable (or REDIS_URL is not set), automatically falls back
to an in-memory dict so the app still works without any external services.

Keys used (all prefixed with "fraud:"):
  fraud:loc:{user_id}          HASH  → {lat, lon, timestamp, city}
  fraud:txn_ts:{user_id}       ZSET  → {txn_id: unix_timestamp}  (score = ts)
  fraud:fail_ts:{user_id}      ZSET  → {txn_id: unix_timestamp}  (failed txns)
"""
import json
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── In-memory fallback stores ─────────────────────────────────────────────────
# These mimic what Redis would hold per user.
_mem_loc:  dict[str, dict] = {}          # user_id → {lat, lon, timestamp, city}
_mem_txns: dict[str, list] = {}          # user_id → [(score_ts, member), …]
_mem_fail: dict[str, list] = {}          # user_id → [(score_ts, member), …]

_redis_client = None   # set by init_redis()
_using_redis  = False


def init_redis(redis_url: str) -> bool:
    """
    Try to connect to Redis. Returns True on success, False if Redis is
    unavailable (the app will use the in-memory fallback silently).
    """
    global _redis_client, _using_redis
    if not redis_url:
        logger.warning("[redis_store] REDIS_URL not set — using in-memory fallback.")
        return False
    try:
        import redis as _redis
        client = _redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
        client.ping()   # raises ConnectionError if Redis is down
        _redis_client = client
        _using_redis = True
        logger.info("[redis_store] Connected to Redis at %s", redis_url)
        return True
    except Exception as exc:
        logger.warning("[redis_store] Redis unavailable (%s) — using in-memory fallback.", exc)
        return False


def is_redis_available() -> bool:
    return _using_redis


# ─────────────────────────────────────────────────────────────────────────────
# Last location helpers
# ─────────────────────────────────────────────────────────────────────────────
def set_last_location(user_id: str, lat: float, lon: float,
                       city: str, timestamp: float, ttl: int = 900) -> None:
    """Store the user's most recent transaction location + time."""
    data = {"lat": str(lat), "lon": str(lon),
            "city": city, "timestamp": str(timestamp)}
    if _using_redis:
        key = f"fraud:loc:{user_id}"
        _redis_client.hset(key, mapping=data)
        _redis_client.expire(key, ttl)
    else:
        _mem_loc[user_id] = {"lat": lat, "lon": lon,
                              "city": city, "timestamp": timestamp}


def get_last_location(user_id: str) -> Optional[dict]:
    """
    Return the last stored location for user_id, or None if not found.
    Result dict: {lat: float, lon: float, city: str, timestamp: float}
    """
    if _using_redis:
        key = f"fraud:loc:{user_id}"
        raw = _redis_client.hgetall(key)
        if not raw:
            return None
        return {"lat": float(raw["lat"]), "lon": float(raw["lon"]),
                "city": raw["city"], "timestamp": float(raw["timestamp"])}
    else:
        return _mem_loc.get(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# Recent transaction timestamp helpers (sorted set / list)
# ─────────────────────────────────────────────────────────────────────────────
def add_txn_timestamp(user_id: str, txn_id: str,
                       ts: float, ttl: int = 900) -> None:
    """Add a transaction timestamp to the user's recent-txn log."""
    if _using_redis:
        key = f"fraud:txn_ts:{user_id}"
        _redis_client.zadd(key, {txn_id: ts})
        _redis_client.expire(key, ttl)
    else:
        lst = _mem_txns.setdefault(user_id, [])
        lst.append((ts, txn_id))
        # Keep list sorted by timestamp
        lst.sort(key=lambda x: x[0])


def count_recent_txns(user_id: str, window_seconds: float) -> int:
    """Count how many transactions occurred within the last `window_seconds`."""
    cutoff = time.time() - window_seconds
    if _using_redis:
        key = f"fraud:txn_ts:{user_id}"
        return _redis_client.zcount(key, cutoff, "+inf")
    else:
        lst = _mem_txns.get(user_id, [])
        # Prune old entries first
        _mem_txns[user_id] = [(t, m) for t, m in lst if t >= cutoff]
        return len(_mem_txns[user_id])


# ─────────────────────────────────────────────────────────────────────────────
# Recent failure timestamp helpers
# ─────────────────────────────────────────────────────────────────────────────
def add_fail_timestamp(user_id: str, txn_id: str,
                        ts: float, ttl: int = 900) -> None:
    """Record a failed transaction timestamp."""
    if _using_redis:
        key = f"fraud:fail_ts:{user_id}"
        _redis_client.zadd(key, {txn_id: ts})
        _redis_client.expire(key, ttl)
    else:
        lst = _mem_fail.setdefault(user_id, [])
        lst.append((ts, txn_id))
        lst.sort(key=lambda x: x[0])


def count_recent_failures(user_id: str, window_seconds: float) -> int:
    """Count failed transactions within the last `window_seconds`."""
    cutoff = time.time() - window_seconds
    if _using_redis:
        key = f"fraud:fail_ts:{user_id}"
        return _redis_client.zcount(key, cutoff, "+inf")
    else:
        lst = _mem_fail.get(user_id, [])
        _mem_fail[user_id] = [(t, m) for t, m in lst if t >= cutoff]
        return len(_mem_fail[user_id])
