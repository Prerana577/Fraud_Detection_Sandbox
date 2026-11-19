"""
routes/stats.py — Aggregated dashboard statistics.

Endpoints:
  GET /api/stats   — totals, fraud rate, per-rule counts, frozen accounts
"""
import logging
from flask import Blueprint, jsonify
from sqlalchemy import func

from models import db, Transaction, User, Alert, NetworkEdge

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


@stats_bp.route("/rings", methods=["GET"])
def get_rings():
    """Return detected fraud rings and network link data."""
    from ring_detection import detect_fraud_rings, get_shared_location_users
    txns = Transaction.query.order_by(Transaction.timestamp.desc()).limit(300).all()
    rings = detect_fraud_rings(txns, window_seconds=600)
    shared_locs = get_shared_location_users(txns, window_seconds=120)

    nodes = []
    edges = []
    seen_nodes = set()

    for t in txns[:80]:
        u_node_id = f"user_{t.user_id}"
        m_node_id = f"merch_{t.merchant.replace(' ', '_')}"

        if u_node_id not in seen_nodes:
            seen_nodes.add(u_node_id)
            nodes.append({
                "id": u_node_id,
                "label": getattr(t.user, "name", t.user_id),
                "type": "user",
                "status": getattr(t.user, "status", "active"),
                "city": t.city
            })

        if m_node_id not in seen_nodes:
            seen_nodes.add(m_node_id)
            nodes.append({
                "id": m_node_id,
                "label": t.merchant,
                "type": "merchant",
                "city": t.city
            })

        edges.append({
            "source": u_node_id,
            "target": m_node_id,
            "decision": t.decision,
            "amount": t.amount,
            "risk_score": t.risk_score,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None
        })

    return jsonify({
        "rings": rings,
        "shared_locations": shared_locs,
        "graph": {
            "nodes": nodes,
            "edges": edges
        }
    })



@stats_bp.route("/reset", methods=["POST"])
def reset_database():
    """
    Wipe all transactions, alerts, and network edges.
    Unfreeze all users and reset avg_amount to 2000.
    Keeps the user records so the sandbox is ready for a fresh CSV upload.
    """
    try:
        # Order matters: alerts FK → transactions, network_edges standalone
        Alert.query.delete()
        Transaction.query.delete()
        NetworkEdge.query.delete()

        # Reset all users to clean baseline
        users = User.query.all()
        for u in users:
            u.status = "active"
            u.avg_amount = 2000.0

        db.session.commit()

        remaining_users = User.query.count()
        logger.info("[reset] Database wiped. %d users retained and reset.", remaining_users)

        return jsonify({
            "status": "success",
            "message": f"Database reset complete. {remaining_users} users retained (all active, avg_amount reset). 0 transactions, 0 alerts, 0 network edges.",
            "users_retained": remaining_users,
        })
    except Exception as exc:
        db.session.rollback()
        logger.error("[reset] Failed: %s", exc, exc_info=True)
        return jsonify({"status": "error", "error": str(exc)}), 500
