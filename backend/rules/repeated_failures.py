"""
rules/repeated_failures.py — Repeated Transaction Failures rule.

Concept:
    Multiple failed transactions in a short window often indicate someone
    trying different cards / PINs, or an attacker probing card limits.

    Side-effect: if ≥ MIN_FAILURES failures within WINDOW_SECONDS, the user's
    account is automatically frozen (handled by the scoring pipeline after this
    rule fires — we return a flag in the reason dict).

Algorithm:
    1. Count the user's failed transactions in the last WINDOW_SECONDS from Redis.
    2. If count ≥ MIN_FAILURES → return (points, reason_dict, freeze=True)

Time complexity: O(log N) — Redis ZCOUNT on a sorted set.
"""
from typing import Optional, Tuple

import redis_store


def check_repeated_failures(
    user_id: str,
    txn_status: str,       # "success" | "failed"
    rule_cfg: dict,        # rule_config["repeated_failures"]
    **_kwargs,
) -> Optional[Tuple[int, dict]]:
    """
    Returns (points, reason_dict) if repeated failures are detected, else None.
    The reason_dict includes a "freeze_account" key set to True when the account
    should be frozen — the scoring pipeline acts on this flag.
    """
    min_failures = rule_cfg.get("min_failures", 3)
    window       = rule_cfg.get("window_seconds", 600)
    points       = rule_cfg.get("points", 30)

    count = redis_store.count_recent_failures(user_id, window_seconds=window)

    if count >= min_failures:
        detail = (
            f"Repeated failures: {count} failed transactions in the last "
            f"{window // 60} min — account will be frozen"
        )
        return points, {
            "rule":           "repeated_failures",
            "points":         points,
            "detail":         detail,
            "freeze_account": True,   # signal to scoring.py
        }

    return None
