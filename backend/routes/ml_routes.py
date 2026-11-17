"""
routes/ml_routes.py — IsolationForest Machine Learning vs Rule-Based Comparison API.

Endpoints:
  GET  /api/ml/compare   — Metrics, agreement rate, confusion breakdown, and recent comparison list
  POST /api/ml/retrain   — Re-train IsolationForest on current historical transactions
"""
import logging
from flask import Blueprint, jsonify, request
from models import db, Transaction, User
from ml_model import ml_detector, rf_detector, compute_ml_metrics

logger = logging.getLogger(__name__)
ml_bp = Blueprint("ml", __name__, url_prefix="/api/ml")


@ml_bp.route("/compare", methods=["GET"])
def get_ml_comparison():
    """
    Compare Rule-based decisions against IsolationForest ML predictions for recent transactions.
    """
    limit = min(int(request.args.get("limit", 100)), 200)
    txns = Transaction.query.order_by(Transaction.timestamp.desc()).limit(limit).all()
    users = {u.user_id: u.avg_amount for u in User.query.all()}

    comparisons = []
    both_flagged = 0       # Rules: FLAG/BLOCK, ML: ANOMALY
    both_clean = 0         # Rules: APPROVE,    ML: NORMAL
    rules_only = 0         # Rules: FLAG/BLOCK, ML: NORMAL (ML false negative or rule over-strict)
    ml_only = 0            # Rules: APPROVE,    ML: ANOMALY (ML false positive or rule missed)

    for txn in txns:
        avg = users.get(txn.user_id, 2000.0)
        ts = txn.timestamp.timestamp()
        ml_res = ml_detector.predict(txn.amount, avg, ts, txn.txn_status)

        rule_fraud = txn.decision in ("FLAG", "BLOCK")
        ml_fraud = ml_res["is_anomaly"]

        if rule_fraud and ml_fraud:
            both_flagged += 1
            status = "AGREED_FRAUD"
        elif not rule_fraud and not ml_fraud:
            both_clean += 1
            status = "AGREED_NORMAL"
        elif rule_fraud and not ml_fraud:
            rules_only += 1
            status = "RULES_ONLY"
        else:
            ml_only += 1
            status = "ML_ONLY"

        comparisons.append({
            "txn_id": txn.txn_id,
            "user_id": txn.user_id,
            "amount": txn.amount,
            "city": txn.city,
            "merchant": txn.merchant,
            "timestamp": txn.timestamp.isoformat(),
            "rule_score": txn.risk_score,
            "rule_decision": txn.decision,
            "ml_decision": ml_res["ml_decision"],
            "ml_anomaly_score": ml_res["anomaly_score"],
            "comparison_status": status,
        })

    total = len(comparisons)
    agreement_count = both_flagged + both_clean
    agreement_rate = round((agreement_count / total * 100), 1) if total > 0 else 100.0

    return jsonify({
        "total_analyzed": total,
        "agreement_rate": agreement_rate,
        "matrix": {
            "both_flagged": both_flagged,
            "both_clean": both_clean,
            "rules_only": rules_only,
            "ml_only": ml_only,
        },
        "model_info": {
            "algorithm": "IsolationForest (Unsupervised)",
            "contamination": ml_detector.contamination,
            "is_fitted": ml_detector.is_fitted,
        },
        "comparisons": comparisons,
    })


@ml_bp.route("/retrain", methods=["POST"])
def retrain_model():
    """Retrain the model on database transactions."""
    txns = Transaction.query.all()
    user_map = {u.user_id: u.avg_amount for u in User.query.all()}
    ml_detector.fit_from_transactions(txns, user_map)
    return jsonify({
        "status": "success",
        "sample_count": len(txns),
        "message": f"IsolationForest successfully retrained on {len(txns)} transactions."
    })


@ml_bp.route("/metrics", methods=["GET"])
def get_ml_metrics():
    """Return precision/recall/F1 for IsolationForest and RandomForest vs ground-truth labels."""
    txns = Transaction.query.all()
    user_avg_map = {u.user_id: u.avg_amount for u in User.query.all()}
    result = compute_ml_metrics(txns, user_avg_map)
    return jsonify(result)


@ml_bp.route("/retrain-supervised", methods=["POST"])
def retrain_supervised():
    """Retrain the RandomForestClassifier on labeled (non-FLAG) transactions."""
    txns = Transaction.query.all()
    user_avg_map = {u.user_id: u.avg_amount for u in User.query.all()}
    rf_detector.fit_from_transactions(txns, user_avg_map)
    return jsonify({"status": "retrained", "count": len(txns)})


@ml_bp.route("/rf-compare", methods=["GET"])
def get_rf_comparison():
    """
    Compare Rule-based decisions against both IsolationForest and RandomForest predictions.
    Extends /api/ml/compare by adding rf_decision and fraud_probability per transaction.
    """
    limit = min(int(request.args.get("limit", 100)), 200)
    txns = Transaction.query.order_by(Transaction.timestamp.desc()).limit(limit).all()
    users = {u.user_id: u.avg_amount for u in User.query.all()}

    comparisons = []
    both_flagged = 0
    both_clean = 0
    rules_only = 0
    ml_only = 0

    for txn in txns:
        avg = users.get(txn.user_id, 2000.0)
        ts = txn.timestamp.timestamp()
        if_res = ml_detector.predict(txn.amount, avg, ts, txn.txn_status)
        rf_res = rf_detector.predict(txn.amount, avg, ts, txn.txn_status)

        rule_fraud = txn.decision in ("FLAG", "BLOCK")
        ml_fraud = if_res["is_anomaly"]

        if rule_fraud and ml_fraud:
            both_flagged += 1
            status = "AGREED_FRAUD"
        elif not rule_fraud and not ml_fraud:
            both_clean += 1
            status = "AGREED_NORMAL"
        elif rule_fraud and not ml_fraud:
            rules_only += 1
            status = "RULES_ONLY"
        else:
            ml_only += 1
            status = "ML_ONLY"

        comparisons.append({
            "txn_id": txn.txn_id,
            "user_id": txn.user_id,
            "amount": txn.amount,
            "city": txn.city,
            "merchant": txn.merchant,
            "timestamp": txn.timestamp.isoformat(),
            "rule_score": txn.risk_score,
            "rule_decision": txn.decision,
            "ml_decision": if_res["ml_decision"],
            "ml_anomaly_score": if_res["anomaly_score"],
            "rf_decision": rf_res["rf_decision"],
            "fraud_probability": rf_res["fraud_probability"],
            "comparison_status": status,
        })

    total = len(comparisons)
    agreement_count = both_flagged + both_clean
    agreement_rate = round((agreement_count / total * 100), 1) if total > 0 else 100.0

    return jsonify({
        "total_analyzed": total,
        "agreement_rate": agreement_rate,
        "matrix": {
            "both_flagged": both_flagged,
            "both_clean": both_clean,
            "rules_only": rules_only,
            "ml_only": ml_only,
        },
        "model_info": {
            "algorithm": "IsolationForest + RandomForest",
            "contamination": ml_detector.contamination,
            "if_fitted": ml_detector.is_fitted,
            "rf_fitted": rf_detector.is_fitted,
        },
        "comparisons": comparisons,
    })
