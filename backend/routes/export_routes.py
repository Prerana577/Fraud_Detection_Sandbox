"""
routes/export_routes.py — CSV export endpoints.

Endpoints:
  GET /api/export/transactions.csv  — All transactions as CSV
  GET /api/export/flagged.csv       — Flagged / overridden transactions as CSV
  GET /api/export/alerts.csv        — All alerts as CSV
"""
import csv
import io

from flask import Blueprint, Response

from models import db, Transaction, Alert

export_bp = Blueprint("export", __name__, url_prefix="/api/export")


def _txn_to_row(txn):
    reasons_summary = " | ".join(
        r.get("detail", "") for r in (txn.reasons or []) if r.get("detail")
    )
    return {
        "txn_id": txn.txn_id,
        "user_name": txn.user.name if txn.user else "",
        "amount": txn.amount,
        "merchant": txn.merchant,
        "city": txn.city,
        "timestamp": txn.timestamp.isoformat() if txn.timestamp else "",
        "txn_status": txn.txn_status,
        "risk_score": txn.risk_score,
        "decision": txn.overridden_by or txn.decision,
        "reasons_summary": reasons_summary,
    }


TXN_FIELDS = ["txn_id", "user_name", "amount", "merchant", "city", "timestamp",
               "txn_status", "risk_score", "decision", "reasons_summary"]

ALERT_FIELDS = ["id", "txn_id", "user_id", "message", "created_at", "acknowledged"]


@export_bp.route("/transactions.csv", methods=["GET"])
def export_transactions():
    """Download all transactions as CSV."""
    txns = Transaction.query.order_by(Transaction.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TXN_FIELDS)
    writer.writeheader()
    for txn in txns:
        writer.writerow(_txn_to_row(txn))
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=transactions.csv"},
    )


@export_bp.route("/flagged.csv", methods=["GET"])
def export_flagged():
    """Download flagged / overridden transactions as CSV."""
    txns = (
        Transaction.query
        .filter(
            (Transaction.decision == "FLAG") | (Transaction.overridden_by.isnot(None))
        )
        .order_by(Transaction.timestamp.desc())
        .all()
    )
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=TXN_FIELDS)
    writer.writeheader()
    for txn in txns:
        writer.writerow(_txn_to_row(txn))
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=flagged_transactions.csv"},
    )


@export_bp.route("/alerts.csv", methods=["GET"])
def export_alerts():
    """Download all alerts as CSV."""
    alerts = Alert.query.order_by(Alert.created_at.desc()).all()
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=ALERT_FIELDS)
    writer.writeheader()
    for a in alerts:
        writer.writerow({
            "id": a.id,
            "txn_id": a.txn_id,
            "user_id": a.user_id,
            "message": a.message,
            "created_at": a.created_at.isoformat() if a.created_at else "",
            "acknowledged": a.acknowledged,
        })
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=alerts.csv"},
    )
