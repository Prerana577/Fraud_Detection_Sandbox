"""
ring_detection.py — Fraud ring and shared-location detection utilities.

Functions:
  detect_fraud_rings(transactions, window_seconds=300) -> list[dict]
  get_shared_location_users(transactions, window_seconds=60) -> list[dict]
"""
from datetime import datetime, timezone


def _to_ts(txn):
    """Return a comparable float timestamp from a transaction object."""
    ts = txn.timestamp
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts).timestamp()
        except Exception:
            return 0.0
    if isinstance(ts, datetime):
        return ts.timestamp()
    return 0.0


def detect_fraud_rings(transactions, window_seconds=300):
    """
    Find groups of 3+ different users sharing (city, merchant) within window_seconds.

    Returns list of:
      {
        "ring_id": int,
        "city": str,
        "merchant": str,
        "user_ids": [str],
        "txn_ids": [str],
        "txn_count": int,
        "window_start": str (ISO),
        "window_end": str (ISO),
      }
    """
    sorted_txns = sorted(transactions, key=_to_ts)
    rings = []
    ring_id = 0

    for i, anchor in enumerate(sorted_txns):
        anchor_ts = _to_ts(anchor)
        city = getattr(anchor, "city", None)
        merchant = getattr(anchor, "merchant", None)
        if not city or not merchant:
            continue

        group_users = {str(anchor.user_id)}
        group_txn_ids = [str(anchor.txn_id)]
        group_ts = [anchor_ts]

        for j in range(i + 1, len(sorted_txns)):
            other = sorted_txns[j]
            other_ts = _to_ts(other)
            if other_ts - anchor_ts > window_seconds:
                break
            if (
                getattr(other, "city", None) == city
                and getattr(other, "merchant", None) == merchant
                and str(other.user_id) not in group_users
            ):
                group_users.add(str(other.user_id))
                group_txn_ids.append(str(other.txn_id))
                group_ts.append(other_ts)

        if len(group_users) >= 3:
            # Avoid duplicate rings (same set already reported)
            existing = any(
                set(r["user_ids"]) == group_users
                and r["city"] == city
                and r["merchant"] == merchant
                for r in rings
            )
            if not existing:
                ring_id += 1
                rings.append({
                    "ring_id": ring_id,
                    "city": city,
                    "merchant": merchant,
                    "user_ids": sorted(group_users),
                    "txn_ids": group_txn_ids,
                    "txn_count": len(group_txn_ids),
                    "window_start": datetime.fromtimestamp(min(group_ts), tz=timezone.utc).isoformat(),
                    "window_end": datetime.fromtimestamp(max(group_ts), tz=timezone.utc).isoformat(),
                })

    return rings


def get_shared_location_users(transactions, window_seconds=60):
    """
    Find pairs/groups of 2+ different users in the same city within window_seconds.

    Returns list of:
      {
        "city": str,
        "user_ids": [str],
        "txn_count": int,
        "window_start": str (ISO),
        "window_end": str (ISO),
      }
    """
    sorted_txns = sorted(transactions, key=_to_ts)
    groups = []

    for i, anchor in enumerate(sorted_txns):
        anchor_ts = _to_ts(anchor)
        city = getattr(anchor, "city", None)
        if not city:
            continue

        group_users = {str(anchor.user_id)}
        group_ts = [anchor_ts]

        for j in range(i + 1, len(sorted_txns)):
            other = sorted_txns[j]
            other_ts = _to_ts(other)
            if other_ts - anchor_ts > window_seconds:
                break
            if (
                getattr(other, "city", None) == city
                and str(other.user_id) not in group_users
            ):
                group_users.add(str(other.user_id))
                group_ts.append(other_ts)

        if len(group_users) >= 2:
            existing = any(
                set(g["user_ids"]) == group_users and g["city"] == city
                for g in groups
            )
            if not existing:
                groups.append({
                    "city": city,
                    "user_ids": sorted(group_users),
                    "txn_count": len(group_ts),
                    "window_start": datetime.fromtimestamp(min(group_ts), tz=timezone.utc).isoformat(),
                    "window_end": datetime.fromtimestamp(max(group_ts), tz=timezone.utc).isoformat(),
                })

    return groups
