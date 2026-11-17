"""
routes/stats.py — Aggregated dashboard statistics.

Endpoints:
  GET /api/stats   — totals, fraud rate, per-rule counts, frozen accounts
"""
import logging
from flask import Blueprint, jsonify
from sqlalchemy import func

from models import db, Transaction, User, Alert

logger = logging.getLogger(__name__)
stats_bp = Blueprint("stats", __name__, url_prefix="/api")


@stats_bp.route("/stats", methods=["GET"])
def get_stats():
    """
    Return a statistics summary for the dashboard KPI cards and charts.

    Response shape:
    {
      total, approved, flagged, blocked, fraud_rate,
      avg_risk_score, frozen_accounts,
      rule_triggers: {rule_name: count, …}
    }
    """
    # ── Decision counts ───────────────────────────────────────────────────────
    rows = (
        db.session.query(Transaction.decision, func.count(Transaction.txn_id))
        .group_by(Transaction.decision)
        .all()
    )
    counts = {r[0]: r[1] for r in rows}
    approved = counts.get("APPROVE", 0)
    flagged  = counts.get("FLAG", 0)
    blocked  = counts.get("BLOCK", 0)
    total    = approved + flagged + blocked

    fraud_rate = round((flagged + blocked) / total * 100, 1) if total else 0.0

    # ── Average risk score ────────────────────────────────────────────────────
    avg_score = db.session.query(func.avg(Transaction.risk_score)).scalar() or 0
    avg_score = round(float(avg_score), 1)

    # ── Frozen accounts ───────────────────────────────────────────────────────
    frozen_accounts = User.query.filter_by(status="frozen").count()

    # ── Per-rule trigger counts ───────────────────────────────────────────────
    # reasons is a JSON column: [{rule, points, detail}, …]
    # We iterate in Python — acceptable for dashboard polling (not real-time hot path)
    rule_triggers: dict[str, int] = {}
    all_reasons = db.session.query(Transaction.reasons).all()
    for (reasons,) in all_reasons:
        if not reasons:
            continue
        for reason in reasons:
            rule = reason.get("rule", "unknown")
            rule_triggers[rule] = rule_triggers.get(rule, 0) + 1

    # ── Unacknowledged alerts ─────────────────────────────────────────────────
    unacked_alerts = Alert.query.filter_by(acknowledged=False).count()

    return jsonify({
        "total":            total,
        "approved":         approved,
        "flagged":          flagged,
        "blocked":          blocked,
        "fraud_rate":       fraud_rate,
        "avg_risk_score":   avg_score,
        "frozen_accounts":  frozen_accounts,
        "rule_triggers":    rule_triggers,
        "unacked_alerts":   unacked_alerts,
    })
