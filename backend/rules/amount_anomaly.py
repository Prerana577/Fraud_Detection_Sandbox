"""
rules/amount_anomaly.py — Amount Anomaly rule.

Concept:
    A transaction amount that is much larger than the user's historical average
    is suspicious (e.g., someone steals a card and splurges).

Two detection methods (either can trigger):
    1. Multiplier check : amount > MULTIPLIER × user.avg_amount
    2. Z-score check    : (amount - avg) / std_dev > ZSCORE_THRESHOLD
       (We estimate std_dev as 40% of avg_amount — realistic for spending data.)

Time complexity: O(1) — reads avg_amount from the User object (already in memory).
"""
from typing import Optional, Tuple


# A simple heuristic for std-dev when we don't have the full distribution.
# Standard deviation ≈ 40% of mean is typical for consumer spending data.
_STD_DEV_RATIO = 0.40


def check_amount_anomaly(
    amount: float,
    avg_amount: float,
    rule_cfg: dict,       # rule_config["amount_anomaly"]
    **_kwargs,
) -> Optional[Tuple[int, dict]]:
    """
    Returns (points, reason_dict) if amount is anomalously large, else None.
    """
    multiplier  = rule_cfg.get("multiplier", 3.0)
    z_threshold = rule_cfg.get("zscore_threshold", 3.0)
    points      = rule_cfg.get("points", 25)

    if avg_amount <= 0:
        return None   # Avoid division by zero for brand-new users

    ratio = amount / avg_amount
    std_dev = avg_amount * _STD_DEV_RATIO
    z_score = (amount - avg_amount) / std_dev if std_dev > 0 else 0

    triggered = False
    trigger_reason = ""

    if ratio > multiplier:
        triggered = True
        trigger_reason = (
            f"Amount ₹{amount:,.0f} is {ratio:.1f}× the user's average "
            f"(₹{avg_amount:,.0f})"
        )
    elif z_score > z_threshold:
        triggered = True
        trigger_reason = (
            f"Amount ₹{amount:,.0f} has z-score {z_score:.1f} "
            f"(threshold: {z_threshold})"
        )

    if triggered:
        return points, {
            "rule":   "amount_anomaly",
            "points": points,
            "detail": trigger_reason,
        }

    return None
