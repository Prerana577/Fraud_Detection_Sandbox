"""
rules/impossible_travel.py — Impossible Travel rule.

Concept:
    If the user's last recorded location and the current transaction location
    imply a travel speed greater than SPEED_THRESHOLD_KMH, it is physically
    impossible (even by the fastest commercial aircraft ≈ 900 km/h).

Algorithm:
    1. Fetch last known location from Redis (lat, lon, timestamp, city).
    2. Compute Haversine distance between the two points.
    3. Compute elapsed time in hours.
    4. speed_kmh = distance_km / elapsed_hours
    5. If speed_kmh > threshold → return (points, reason_dict)

Haversine formula (great-circle distance):
    a = sin²(Δlat/2) + cos(lat1)·cos(lat2)·sin²(Δlon/2)
    c = 2·atan2(√a, √(1-a))
    d = R·c          where R = 6371 km (Earth's mean radius)

Time complexity: O(1) — single Redis HGET + constant arithmetic.
"""
import math
import time
from typing import Optional, Tuple

import redis_store


# Earth's mean radius in kilometres
_EARTH_RADIUS_KM = 6371.0


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Return the great-circle distance in kilometres between two points
    on Earth specified by decimal-degree latitude/longitude.
    Includes fast-path for co-located transactions to minimize trigonometric CPU cycles.
    """
    # Fast path: identical or sub-meter coordinates
    if abs(lat1 - lat2) < 1e-6 and abs(lon1 - lon2) < 1e-6:
        return 0.0

    # Convert degrees → radians
    r_lat1, r_lon1, r_lat2, r_lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = r_lat2 - r_lat1
    dlon = r_lon2 - r_lon1

    a = math.sin(dlat / 2) ** 2 + math.cos(r_lat1) * math.cos(r_lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_KM * c


def check_impossible_travel(
    user_id: str,
    lat: float,
    lon: float,
    city: str,
    timestamp: float,        # Unix epoch (seconds)
    rule_cfg: dict,          # rule_config["impossible_travel"]
    **_kwargs,               # absorb extra keyword args passed by scoring pipeline
) -> Optional[Tuple[int, dict]]:
    """
    Returns (points, reason_dict) if impossible travel is detected, else None.

    reason_dict keys: rule, points, detail
    """
    last = redis_store.get_last_location(user_id)
    if last is None:
        # No previous location — can't evaluate the rule (first transaction)
        return None

    prev_lat  = last["lat"]
    prev_lon  = last["lon"]
    prev_city = last["city"]
    prev_ts   = last["timestamp"]

    elapsed_seconds = timestamp - prev_ts
    if elapsed_seconds <= 0:
        # Same second or clock skew — skip to avoid division by zero
        return None

    distance_km  = _haversine(prev_lat, prev_lon, lat, lon)
    elapsed_hours = elapsed_seconds / 3600.0
    speed_kmh    = distance_km / elapsed_hours

    threshold = rule_cfg.get("speed_threshold_kmh", 900)
    points    = rule_cfg.get("points", 50)

    if speed_kmh > threshold:
        # Format elapsed time for the human-readable reason
        elapsed_min = int(elapsed_seconds / 60)
        elapsed_str = (
            f"{elapsed_min} min"
            if elapsed_seconds < 3600
            else f"{elapsed_hours:.1f} hr"
        )
        detail = (
            f"Impossible travel: {prev_city} → {city} "
            f"in {elapsed_str} (~{distance_km:.0f} km, "
            f"implied speed {speed_kmh:.0f} km/h)"
        )
        return points, {
            "rule":   "impossible_travel",
            "points": points,
            "detail": detail,
        }

    return None
