"""
routes/replay_routes.py — CSV replay endpoints (background thread simulation).

Endpoints:
  GET  /api/replay/status  — Current replay state
  POST /api/replay/start   — Start replaying a CSV file
  POST /api/replay/stop    — Stop an in-progress replay
"""
import csv
import threading
import logging

from flask import Blueprint, request, jsonify, current_app

from models import User

logger = logging.getLogger(__name__)

replay_bp = Blueprint("replay", __name__, url_prefix="/api/replay")

_replay_state = {
    "mode": "live",
    "file": None,
    "processed": 0,
    "total": 0,
    "running": False,
}


@replay_bp.route("/status", methods=["GET"])
def replay_status():
    """Return the current replay state."""
    return jsonify(dict(_replay_state))


@replay_bp.route("/start", methods=["POST"])
def replay_start():
    """
    Start replaying a CSV file in a background thread.

    JSON body: { "file": "sample_dataset.csv" }
    """
    data = request.get_json(silent=True) or {}
    filename = str(data.get("file", "sample_dataset.csv")).strip()

    # Sanitise — only allow simple filenames, no path traversal
    if "/" in filename or "\\" in filename or ".." in filename:
        return jsonify({"error": "Invalid filename"}), 400

    filepath = f"/Users/prajwalkv/Downloads/FinTech/fraud-sandbox/{filename}"

    try:
        with open(filepath, newline="", encoding="utf-8") as fh:
            reader = list(csv.DictReader(fh))
    except FileNotFoundError:
        return jsonify({"error": f"File not found: {filename}"}), 404
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    rows = reader[:200]
    total = len(rows)

    _replay_state.update({
        "mode": "replay",
        "file": filename,
        "processed": 0,
        "total": total,
        "running": True,
    })

    app = current_app._get_current_object()

    def _run():
        with app.app_context():
            from routes.transactions import process_transaction

            first_user = User.query.first()
            user_id = first_user.user_id if first_user else "user_default"

            for row in rows:
                if not _replay_state["running"]:
                    break

                # Flexible amount mapping
                amount_raw = (
                    row.get("amount_inr") or row.get("amount") or
                    row.get("amt") or row.get("amt_inr") or
                    row.get("trans_amount") or row.get("price") or row.get("val")
                )
                try:
                    amount = float(amount_raw) if amount_raw else 1000.0
                except (ValueError, TypeError):
                    amount = 1000.0

                payload = {
                    "user_id": user_id,
                    "amount": amount,
                    "merchant": "CSV Import",
                    "city": "Mumbai",
                    "lat": 19.076,
                    "lon": 72.877,
                    "txn_status": "success",
                }

                try:
                    process_transaction(payload)
                except Exception as exc:
                    logger.warning("[replay] Row error: %s", exc)

                _replay_state["processed"] += 1

            _replay_state["running"] = False
            logger.info("[replay] Finished: %d/%d rows processed.", _replay_state["processed"], total)

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return jsonify({"started": True, "total": total})


@replay_bp.route("/stop", methods=["POST"])
def replay_stop():
    """Stop an in-progress replay."""
    _replay_state["running"] = False
    return jsonify({"stopped": True})
