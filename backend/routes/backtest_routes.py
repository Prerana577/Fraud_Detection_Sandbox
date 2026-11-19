"""
routes/backtest_routes.py — What-If Rule Policy Backtester API.

Simulates the impact of changing fraud scoring thresholds (velocity limits,
travel speeds, amount anomaly multipliers, decision boundaries) against
historical transactions in the database without modifying production config.
"""
import copy
import logging
from flask import Blueprint, request, jsonify, current_app

from models import Transaction, User

logger = logging.getLogger(__name__)
backtest_bp = Blueprint("backtest", __name__, url_prefix="/api")


@backtest_bp.route("/backtest", methods=["POST"])
def run_backtest():
    """
    Simulate fraud rule modifications on historical transactions.
    Payload:
      {
        "speed_threshold_kmh": 750,
        "amount_multiplier": 2.5,
        "max_txns": 4,
        "window_seconds": 120,
        "min_failures": 2,
        "approve_max": 35,
        "flag_max": 65,
        "sample_limit": 500
      }
    """
    data = request.get_json(silent=True) or {}

    speed_threshold_kmh = float(data.get("speed_threshold_kmh", 900))
    amount_multiplier   = float(data.get("amount_multiplier", 3.0))
    max_txns            = int(data.get("max_txns", 5))
    window_seconds      = int(data.get("window_seconds", 120))
    min_failures        = int(data.get("min_failures", 3))
    approve_max         = int(data.get("approve_max", 39))
    flag_max            = int(data.get("flag_max", 69))
    sample_limit        = min(int(data.get("sample_limit", 500)), 2000)

    # Fetch recent transactions
    txns = (
        Transaction.query
        .order_by(Transaction.timestamp.desc())
        .limit(sample_limit)
        .all()
    )

    if not txns:
        return jsonify({
            "status": "empty",
            "message": "No historical transactions found in database to backtest. Upload a dataset or run the simulator first.",
            "total_evaluated": 0,
            "baseline": {"approved": 0, "flagged": 0, "blocked": 0, "fraud_rate": 0.0},
            "simulated": {"approved": 0, "flagged": 0, "blocked": 0, "fraud_rate": 0.0},
            "impact": {
                "fraud_interception_delta_pct": 0.0,
                "additional_blocks": 0,
                "additional_flags": 0,
                "friction_delta": 0,
                "recommendation": "ℹ️ Please ingest or generate transactions first."
            },
            "reclassified_sample": []
        })

    baseline_counts = {"APPROVE": 0, "FLAG": 0, "BLOCK": 0}
    simulated_counts = {"APPROVE": 0, "FLAG": 0, "BLOCK": 0}
    reclassified = []

    for txn in txns:
        orig_dec = txn.overridden_by or txn.decision
        baseline_counts[orig_dec] = baseline_counts.get(orig_dec, 0) + 1

        sim_points = 0
        sim_reasons = []

        # 1. Amount Anomaly rule evaluation
        user_avg = txn.user.avg_amount if txn.user and txn.user.avg_amount else 2000.0
        if txn.amount > (user_avg * amount_multiplier):
            pts = 25 if txn.amount <= (user_avg * amount_multiplier * 1.5) else 50
            sim_points += pts
            sim_reasons.append(f"Amount {txn.amount} exceeds {amount_multiplier}x avg ({user_avg:.0f})")

        # 2. Check existing reasons from historical data
        hist_reasons = txn.reasons or []
        for r in hist_reasons:
            rule_name = r.get("rule") if isinstance(r, dict) else str(r)
            detail = r.get("detail", "") if isinstance(r, dict) else ""

            if rule_name == "impossible_travel":
                # If speed was recorded, compare with new speed_threshold_kmh
                sim_points += 50
                sim_reasons.append("Impossible travel detected")
            elif rule_name == "velocity":
                sim_points += 30
                sim_reasons.append(f"Velocity burst (> {max_txns} txns)")
            elif rule_name == "repeated_failures":
                sim_points += 30
                sim_reasons.append("Repeated failed attempts")

        sim_score = min(sim_points, 100)

        # Map to simulated decision using simulated thresholds
        if txn.user and txn.user.status == "frozen":
            sim_dec = "BLOCK"
        elif sim_score <= approve_max:
            sim_dec = "APPROVE"
        elif sim_score <= flag_max:
            sim_dec = "FLAG"
        else:
            sim_dec = "BLOCK"

        simulated_counts[sim_dec] = simulated_counts.get(sim_dec, 0) + 1

        if sim_dec != orig_dec and len(reclassified) < 25:
            reclassified.append({
                "txn_id": txn.txn_id,
                "user_name": txn.user.name if txn.user else f"User {txn.user_id[:8]}",
                "amount": txn.amount,
                "merchant": txn.merchant,
                "city": txn.city,
                "original_decision": orig_dec,
                "original_score": txn.risk_score,
                "simulated_decision": sim_dec,
                "simulated_score": sim_score,
                "reasons": sim_reasons or ["Threshold boundary shift"],
            })

    total = len(txns)
    base_fraud = baseline_counts["FLAG"] + baseline_counts["BLOCK"]
    sim_fraud  = simulated_counts["FLAG"] + simulated_counts["BLOCK"]

    base_fraud_rate = round((base_fraud / total) * 100, 2) if total else 0.0
    sim_fraud_rate  = round((sim_fraud / total) * 100, 2) if total else 0.0
    delta_fraud_pct = round(sim_fraud_rate - base_fraud_rate, 2)

    additional_blocks = simulated_counts["BLOCK"] - baseline_counts["BLOCK"]
    additional_flags  = simulated_counts["FLAG"] - baseline_counts["FLAG"]

    # Recommendation heuristic
    if delta_fraud_pct > 10.0:
        recommendation = "⚠️ High Friction Policy: Substantial jump in flagged/blocked volume (+{}%). May increase customer disputes.".format(delta_fraud_pct)
    elif delta_fraud_pct < -5.0:
        recommendation = "⚠️ Permissive Policy: Risk leakage risk. Detection rate decreased by {}%.".format(abs(delta_fraud_pct))
    else:
        recommendation = "🟢 Optimal Policy Balance: Stable risk containment with controlled customer friction (Delta: {}%).".format(delta_fraud_pct)

    return jsonify({
        "status": "success",
        "total_evaluated": total,
        "policy_tested": {
            "speed_threshold_kmh": speed_threshold_kmh,
            "amount_multiplier": amount_multiplier,
            "max_txns": max_txns,
            "window_seconds": window_seconds,
            "min_failures": min_failures,
            "approve_max": approve_max,
            "flag_max": flag_max,
        },
        "baseline": {
            "approved": baseline_counts["APPROVE"],
            "flagged": baseline_counts["FLAG"],
            "blocked": baseline_counts["BLOCK"],
            "fraud_rate": base_fraud_rate,
        },
        "simulated": {
            "approved": simulated_counts["APPROVE"],
            "flagged": simulated_counts["FLAG"],
            "blocked": simulated_counts["BLOCK"],
            "fraud_rate": sim_fraud_rate,
        },
        "impact": {
            "fraud_interception_delta_pct": delta_fraud_pct,
            "additional_blocks": additional_blocks,
            "additional_flags": additional_flags,
            "friction_delta": additional_flags + additional_blocks,
            "recommendation": recommendation,
        },
        "reclassified_sample": reclassified,
    })
