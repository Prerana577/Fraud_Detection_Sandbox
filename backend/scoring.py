"""
scoring.py — Central scoring pipeline for the Fraud Detection Sandbox.

Given a transaction payload and the user record, this module:
  1. Runs every rule in ALL_RULES
  2. Accumulates points (capped at 100)
  3. Maps the score to APPROVE / FLAG / BLOCK
  4. Handles the "frozen account always BLOCK" override
  5. Triggers account freeze if repeated-failures rule fires
  6. Updates Redis with the new location and timestamps

Returns a ScoringResult dataclass with everything the route handler needs.
"""
import time
import logging
from dataclasses import dataclass, field

from rules import ALL_RULES
import redis_store

logger = logging.getLogger(__name__)


def ema_update(current_avg: float, new_amount: float, alpha: float = 0.1) -> float:
    """Exponential Moving Average — updates rolling spend baseline."""
    return round(alpha * new_amount + (1 - alpha) * current_avg, 2)


@dataclass
class ScoringResult:
    score:         int
    decision:      str           # "APPROVE" | "FLAG" | "BLOCK"
    reasons:       list          # [{rule, points, detail}, …]
    freeze_account: bool = False  # True if account should be frozen
    latency_ms:    float = 0.0


def score_transaction(
    *,
    user,           # SQLAlchemy User object
    amount: float,
    lat: float,
    lon: float,
    city: str,
    txn_id: str,
    txn_status: str,   # "success" | "failed"
    timestamp: float,  # Unix epoch (seconds); defaults to now if caller passes time.time()
    rule_config: dict, # from Config.RULE_CONFIG (may be edited at runtime)
) -> ScoringResult:
    """
    Score a transaction and return a ScoringResult.
    This function has no side effects on the database — callers handle DB writes.
    Redis is updated here so subsequent rules within the same request see fresh data.
    """
    _perf_start = time.perf_counter()
    user_id    = user.user_id
    avg_amount = user.avg_amount
    total_points = 0
    reasons      = []
    freeze_flag  = False

    # ── Build the kwargs dict passed to every rule ────────────────────────────
    rule_kwargs = dict(
        user_id    = user_id,
        amount     = amount,
        avg_amount = avg_amount,
        lat        = lat,
        lon        = lon,
        city       = city,
        txn_id     = txn_id,
        txn_status = txn_status,
        timestamp  = timestamp,
    )

    # ── Run each rule ─────────────────────────────────────────────────────────
    for rule_fn in ALL_RULES:
        rule_name = rule_fn.__module__.split(".")[-1]   # e.g. "impossible_travel"
        cfg = rule_config.get(rule_name, {})
        try:
            result = rule_fn(rule_cfg=cfg, **rule_kwargs)
        except Exception as exc:
            logger.error("[scoring] Rule %s raised an exception: %s", rule_name, exc, exc_info=True)
            result = None

        if result is not None:
            pts, reason = result
            total_points += pts
            reasons.append(reason)
            # Check for the freeze flag signalled by repeated_failures rule
            if reason.get("freeze_account"):
                freeze_flag = True

    # Cap score at 100
    score = min(total_points, 100)

    # ── Determine decision ────────────────────────────────────────────────────
    if user.status == "frozen":
        decision = "BLOCK"
    elif score <= 39:
        decision = "APPROVE"
    elif score <= 69:
        decision = "FLAG"
    else:
        decision = "BLOCK"

    # ── Update Redis AFTER scoring (so this txn counts for future ones) ───────
    ttl = 900  # 15 minutes
    redis_store.set_last_location(user_id, lat, lon, city, timestamp, ttl=ttl)
    redis_store.add_txn_timestamp(user_id, txn_id, timestamp, ttl=ttl)
    if txn_status == "failed":
        redis_store.add_fail_timestamp(user_id, txn_id, timestamp, ttl=ttl)

    logger.debug(
        "[scoring] user=%s score=%d decision=%s reasons=%s",
        user_id, score, decision, [r["rule"] for r in reasons]
    )

    _latency_ms = round((time.perf_counter() - _perf_start) * 1000, 2)

    return ScoringResult(
        score=score,
        decision=decision,
        reasons=reasons,
        freeze_account=freeze_flag,
        latency_ms=_latency_ms,
    )
