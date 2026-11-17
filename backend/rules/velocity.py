"""
rules/velocity.py — Velocity / Transaction Rate rule.

Concept:
    A cardholder making more than MAX_TXNS transactions within a short window
    (WINDOW_SECONDS) is a strong signal of automated card abuse or stolen card.

Algorithm:
    1. Count the user's transactions in the last WINDOW_SECONDS from Redis.
    2. If count > MAX_TXNS → return (points, reason_dict)

Time complexity: O(log N) — Redis ZCOUNT on a sorted set with N elements.
"""
from typing import Optional, Tuple

import redis_store


def check_velocity(
    user_id: str,
    rule_cfg: dict,       # rule_config["velocity"]
    **_kwargs,
) -> Optional[Tuple[int, dict]]:
    """
    Returns (points, reason_dict) if transaction velocity is too high, else None.
    """
    max_txns = rule_cfg.get("max_txns", 5)
    window   = rule_cfg.get("window_seconds", 120)
    points   = rule_cfg.get("points", 30)

    count = redis_store.count_recent_txns(user_id, window_seconds=window)

    if count > max_txns:
        detail = (
            f"High velocity: {count} transactions in the last "
            f"{window // 60} min (limit: {max_txns})"
        )
        return points, {
            "rule":   "velocity",
            "points": points,
            "detail": detail,
        }

    return None
