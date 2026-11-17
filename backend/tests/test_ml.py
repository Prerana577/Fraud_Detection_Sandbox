"""
tests/test_ml.py — Unit tests for the IsolationForest ML fraud detector.
"""
from ml_model import FraudMLDetector


def test_ml_detector_initialization():
    detector = FraudMLDetector(contamination=0.1)
    assert detector.is_fitted is True


def test_ml_detector_predict_normal():
    detector = FraudMLDetector(contamination=0.05)
    # Normal transaction: ₹800 with ₹1000 avg amount at 2 PM on weekday, success
    res = detector.predict(
        amount=800.0,
        avg_amount=1000.0,
        timestamp=1700045600.0,
        txn_status="success",
    )
    assert "is_anomaly" in res
    assert "anomaly_score" in res
    assert "ml_decision" in res
    assert res["ml_decision"] in ("NORMAL", "ANOMALY")


def test_ml_detector_predict_extreme_anomaly():
    detector = FraudMLDetector(contamination=0.05)
    # Huge spike: ₹85,000 for a user with avg ₹500 at 3 AM, failed status
    res = detector.predict(
        amount=85000.0,
        avg_amount=500.0,
        timestamp=1700010000.0,
        txn_status="failed",
    )
    assert res["is_anomaly"] is True
    assert res["ml_decision"] == "ANOMALY"
    assert res["anomaly_score"] > 50.0
