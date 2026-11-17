"""
tests/test_rules.py — Unit tests for every fraud detection rule.

Key test (from spec):
  Coffee in Bengaluru, then flight booked from Guwahati 5 minutes later
  → must trigger impossible_travel with BLOCK or FLAG decision.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATABASE_URL"] = ""
os.environ["REDIS_URL"] = ""

import pytest
import redis_store

# ─────────────────────────────────────────────────────────────────────────────
# Haversine / Impossible Travel
# ─────────────────────────────────────────────────────────────────────────────

# Known city coordinates
BENGALURU  = (12.9716,  77.5946)
GUWAHATI   = (26.1445,  91.7362)
MUMBAI     = (19.0760,  72.8777)


class TestImpossibleTravel:
    """Tests for rules/impossible_travel.py"""

    def setup_method(self):
        """Clear in-memory Redis store before each test."""
        redis_store._mem_loc.clear()

    def _make_cfg(self, speed=900, points=50):
        return {"speed_threshold_kmh": speed, "points": points}

    def test_bengaluru_to_guwahati_5min_is_impossible(self):
        """
        Coffee in Bengaluru at T=0, then a transaction from Guwahati at T+300s.
        Haversine distance ≈ 1,757 km → implied speed ≈ 21,084 km/h >> 900.
        Rule MUST fire.
        """
        from rules.impossible_travel import check_impossible_travel
        now = time.time()

        # Record Bengaluru transaction in the store
        redis_store.set_last_location(
            "user1", BENGALURU[0], BENGALURU[1], "Bengaluru", now - 300
        )

        result = check_impossible_travel(
            user_id="user1",
            lat=GUWAHATI[0],
            lon=GUWAHATI[1],
            city="Guwahati",
            timestamp=now,
            rule_cfg=self._make_cfg(),
        )

        assert result is not None, "Rule should have fired"
        points, reason = result
        assert points == 50
        assert "impossible_travel" in reason["rule"]
        assert "Bengaluru" in reason["detail"]
        assert "Guwahati" in reason["detail"]
        assert "5 min" in reason["detail"]

    def test_no_previous_location_returns_none(self):
        """First transaction for a user → no previous location → rule skips."""
        from rules.impossible_travel import check_impossible_travel
        result = check_impossible_travel(
            user_id="brand_new_user",
            lat=BENGALURU[0], lon=BENGALURU[1],
            city="Bengaluru", timestamp=time.time(),
            rule_cfg=self._make_cfg(),
        )
        assert result is None

    def test_normal_travel_does_not_fire(self):
        """
        Bengaluru to Mumbai in 2 hours → ~981 km → speed ≈ 490 km/h < 900.
        Rule must NOT fire.
        """
        from rules.impossible_travel import check_impossible_travel
        now = time.time()
        redis_store.set_last_location(
            "user2", BENGALURU[0], BENGALURU[1], "Bengaluru", now - 7200  # 2h ago
        )
        result = check_impossible_travel(
            user_id="user2",
            lat=MUMBAI[0], lon=MUMBAI[1],
            city="Mumbai", timestamp=now,
            rule_cfg=self._make_cfg(),
        )
        assert result is None, f"Should not fire for reasonable flight time. Got: {result}"

    def test_custom_threshold_respected(self):
        """Setting speed_threshold_kmh=100 should catch the Bengaluru→Mumbai flight."""
        from rules.impossible_travel import check_impossible_travel
        now = time.time()
        redis_store.set_last_location(
            "user3", BENGALURU[0], BENGALURU[1], "Bengaluru", now - 7200
        )
        result = check_impossible_travel(
            user_id="user3",
            lat=MUMBAI[0], lon=MUMBAI[1],
            city="Mumbai", timestamp=now,
            rule_cfg=self._make_cfg(speed=100),  # very low threshold
        )
        assert result is not None

    def test_custom_points_returned(self):
        """Custom point values must be returned in the result."""
        from rules.impossible_travel import check_impossible_travel
        now = time.time()
        redis_store.set_last_location(
            "user4", BENGALURU[0], BENGALURU[1], "Bengaluru", now - 60
        )
        result = check_impossible_travel(
            user_id="user4",
            lat=GUWAHATI[0], lon=GUWAHATI[1],
            city="Guwahati", timestamp=now,
            rule_cfg=self._make_cfg(points=75),
        )
        assert result is not None
        assert result[0] == 75


# ─────────────────────────────────────────────────────────────────────────────
# Velocity
# ─────────────────────────────────────────────────────────────────────────────

class TestVelocity:
    """Tests for rules/velocity.py"""

    def setup_method(self):
        redis_store._mem_txns.clear()

    def _cfg(self, max_txns=5, window=120, points=30):
        return {"max_txns": max_txns, "window_seconds": window, "points": points}

    def test_fires_when_over_limit(self):
        from rules.velocity import check_velocity
        now = time.time()
        for i in range(6):  # 6 > 5
            redis_store.add_txn_timestamp("userV", f"txn{i}", now - i)

        result = check_velocity(user_id="userV", rule_cfg=self._cfg())
        assert result is not None
        assert result[0] == 30

    def test_does_not_fire_at_limit(self):
        from rules.velocity import check_velocity
        now = time.time()
        for i in range(5):  # exactly 5 — should NOT fire (limit is "more than 5")
            redis_store.add_txn_timestamp("userV2", f"txn{i}", now - i)

        result = check_velocity(user_id="userV2", rule_cfg=self._cfg())
        assert result is None

    def test_old_txns_outside_window_ignored(self):
        from rules.velocity import check_velocity
        now = time.time()
        # 10 txns but all older than the 2-min window
        for i in range(10):
            redis_store.add_txn_timestamp("userV3", f"txn{i}", now - 300 - i)

        result = check_velocity(user_id="userV3", rule_cfg=self._cfg())
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Amount Anomaly
# ─────────────────────────────────────────────────────────────────────────────

class TestAmountAnomaly:
    """Tests for rules/amount_anomaly.py"""

    def _cfg(self, multiplier=3.0, zscore=3.0, points=25):
        return {"multiplier": multiplier, "zscore_threshold": zscore, "points": points}

    def test_multiplier_fires(self):
        from rules.amount_anomaly import check_amount_anomaly
        # 3.1× the average → should fire
        result = check_amount_anomaly(
            amount=3100.0, avg_amount=1000.0, rule_cfg=self._cfg()
        )
        assert result is not None
        assert result[0] == 25
        assert "₹3,100" in result[1]["detail"]

    def test_normal_amount_passes(self):
        from rules.amount_anomaly import check_amount_anomaly
        result = check_amount_anomaly(
            amount=1200.0, avg_amount=1000.0, rule_cfg=self._cfg()
        )
        assert result is None

    def test_zscore_fires(self):
        from rules.amount_anomaly import check_amount_anomaly
        # avg=1000, std=400 → z = (2200-1000)/400 = 3.0 exactly → triggers at > 3
        result = check_amount_anomaly(
            amount=2201.0, avg_amount=1000.0, rule_cfg=self._cfg()
        )
        assert result is not None

    def test_zero_avg_skipped(self):
        from rules.amount_anomaly import check_amount_anomaly
        result = check_amount_anomaly(
            amount=5000.0, avg_amount=0.0, rule_cfg=self._cfg()
        )
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Repeated Failures
# ─────────────────────────────────────────────────────────────────────────────

class TestRepeatedFailures:
    """Tests for rules/repeated_failures.py"""

    def setup_method(self):
        redis_store._mem_fail.clear()

    def _cfg(self, min_failures=3, window=600, points=30):
        return {"min_failures": min_failures, "window_seconds": window, "points": points}

    def test_fires_at_threshold(self):
        from rules.repeated_failures import check_repeated_failures
        now = time.time()
        for i in range(3):  # exactly 3 → should fire
            redis_store.add_fail_timestamp("userF", f"fail{i}", now - i * 10)

        result = check_repeated_failures(
            user_id="userF", txn_status="failed", rule_cfg=self._cfg()
        )
        assert result is not None
        pts, reason = result
        assert pts == 30
        assert reason["freeze_account"] is True

    def test_does_not_fire_below_threshold(self):
        from rules.repeated_failures import check_repeated_failures
        now = time.time()
        for i in range(2):  # only 2 failures
            redis_store.add_fail_timestamp("userF2", f"fail{i}", now - i * 10)

        result = check_repeated_failures(
            user_id="userF2", txn_status="failed", rule_cfg=self._cfg()
        )
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Scoring pipeline integration
# ─────────────────────────────────────────────────────────────────────────────

class TestScoringPipeline:
    """End-to-end test of the scoring.py orchestrator."""

    def setup_method(self):
        redis_store._mem_loc.clear()
        redis_store._mem_txns.clear()
        redis_store._mem_fail.clear()

    def _make_user(self, status="active", avg=3000.0):
        """Create a mock user object."""
        class MockUser:
            user_id = "score_test_user"
            home_city = "Bengaluru"
            home_lat = 12.9716
            home_lon = 77.5946
            avg_amount = avg
        u = MockUser()
        u.status = status
        return u

    def test_clean_transaction_is_approved(self):
        from scoring import score_transaction
        from config import Config
        user = self._make_user()
        result = score_transaction(
            user=user,
            amount=2500.0,
            lat=12.97, lon=77.59,
            city="Bengaluru",
            txn_id="test-1",
            txn_status="success",
            timestamp=time.time(),
            rule_config=Config.RULE_CONFIG,
        )
        assert result.decision == "APPROVE"
        assert result.score <= 39

    def test_impossible_travel_leads_to_block(self):
        """The spec's canonical test case — Bengaluru → Guwahati in 5 min."""
        from scoring import score_transaction
        from config import Config
        user = self._make_user()
        now = time.time()

        # First txn: Bengaluru (sets last location)
        score_transaction(
            user=user,
            amount=250.0,
            lat=BENGALURU[0], lon=BENGALURU[1],
            city="Bengaluru",
            txn_id="first",
            txn_status="success",
            timestamp=now - 300,
            rule_config=Config.RULE_CONFIG,
        )

        # Second txn: Guwahati 5 minutes later
        result = score_transaction(
            user=user,
            amount=5000.0,
            lat=GUWAHATI[0], lon=GUWAHATI[1],
            city="Guwahati",
            txn_id="second",
            txn_status="success",
            timestamp=now,
            rule_config=Config.RULE_CONFIG,
        )

        assert result.decision in ("FLAG", "BLOCK"), (
            f"Expected FLAG or BLOCK for Bengaluru→Guwahati in 5 min, got {result.decision} "
            f"(score={result.score}, reasons={result.reasons})"
        )
        rule_names = [r["rule"] for r in result.reasons]
        assert "impossible_travel" in rule_names

    def test_frozen_user_always_blocked(self):
        from scoring import score_transaction
        from config import Config
        user = self._make_user(status="frozen")
        result = score_transaction(
            user=user, amount=100.0,
            lat=12.97, lon=77.59,
            city="Bengaluru", txn_id="frozen-test",
            txn_status="success", timestamp=time.time(),
            rule_config=Config.RULE_CONFIG,
        )
        assert result.decision == "BLOCK"

    def test_score_capped_at_100(self):
        """Trigger multiple rules — total should not exceed 100."""
        from scoring import score_transaction
        from config import Config
        user = self._make_user()
        now = time.time()

        # Set a recent Bengaluru location (enables impossible travel)
        redis_store.set_last_location(
            user.user_id, BENGALURU[0], BENGALURU[1], "Bengaluru", now - 60
        )
        # Flood velocity
        for i in range(10):
            redis_store.add_txn_timestamp(user.user_id, f"v{i}", now - i)
        # Flood failures
        for i in range(5):
            redis_store.add_fail_timestamp(user.user_id, f"f{i}", now - i * 30)

        result = score_transaction(
            user=user,
            amount=user.avg_amount * 10,   # also triggers amount anomaly
            lat=GUWAHATI[0], lon=GUWAHATI[1],
            city="Guwahati", txn_id="all-rules",
            txn_status="failed", timestamp=now,
            rule_config=Config.RULE_CONFIG,
        )
        assert result.score <= 100
