"""
test_backtest_and_telemetry.py — Unit tests for Policy Backtester,
Device Fingerprinting, and Sandbox Reset endpoints.
Author: Prerana577
"""
import pytest
from models import User, Transaction, Alert


def test_device_info_resolution(app):
    """Test that Transaction model automatically derives consistent device intelligence."""
    with app.app_context():
        txn = Transaction(
            user_id="U-TEST-99",
            amount=1500.0,
            merchant="Electronics Hub",
            city="Bengaluru",
            lat=12.9716,
            lon=77.5946,
            risk_score=15,
            decision="APPROVE",
            reasons=[],
        )
        data = txn.to_dict()
        assert "device_info" in data
        assert "device_type" in data["device_info"]
        assert "ip_address" in data["device_info"]
        assert "vpn_detected" in data["device_info"]
        assert "device_trust" in data["device_info"]
        assert data["device_info"]["device_trust"] >= 0


def test_device_info_suspicious_override(app):
    """Test that high-risk transactions get flagged with suspicious proxy/Tor intelligence."""
    with app.app_context():
        txn = Transaction(
            user_id="U-RISK-01",
            amount=50000.0,
            merchant="Luxury Watches",
            city="Dubai",
            lat=25.2048,
            lon=55.2708,
            risk_score=85,
            decision="BLOCK",
            reasons=[{"rule": "impossible_travel", "points": 50, "detail": "1200 km/h"}],
        )
        data = txn.to_dict()
        assert data["device_info"]["vpn_detected"] is True
        assert data["device_info"]["device_trust"] < 50


def test_backtest_api_empty_handling(client):
    """Test that /api/backtest handles zero or small datasets gracefully."""
    res = client.post("/api/backtest", json={
        "speed_threshold_kmh": 800,
        "amount_multiplier": 2.5,
        "max_txns": 4
    })
    assert res.status_code == 200
    json_data = res.get_json()
    assert "status" in json_data
    assert "baseline" in json_data
    assert "simulated" in json_data
    assert "impact" in json_data


def test_reset_endpoint(client):
    """Test that /api/reset returns 200 and retains existing user base."""
    res = client.post("/api/reset")
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data["status"] == "success"
    assert "users_retained" in json_data
