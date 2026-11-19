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
        import time
        with app.app_context():
            from routes.transactions import process_transaction
            socketio = current_app.extensions.get("socketio")

            for row in rows:
                if not _replay_state["running"]:
                    break

                clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}

                # Flexible amount mapping
                amount_val = (
                    clean_row.get("amount_inr") or
                    clean_row.get("amount") or
                    clean_row.get("amt") or
                    clean_row.get("amt_inr") or
                    clean_row.get("trans_amount") or
                    clean_row.get("price") or
                    clean_row.get("val")
                )
                if not amount_val:
                    for k, v in clean_row.items():
                        if "amount" in k or k == "amt":
                            amount_val = v
                            break
                try:
                    amount = float(amount_val or 1000.0)
                except (ValueError, TypeError):
                    amount = 1000.0

                user_id = (
                    clean_row.get("user_id") or
                    clean_row.get("customer_id") or
                    clean_row.get("card_id") or
                    clean_row.get("nameorig") or
                    "user_01"
                )
                merchant = clean_row.get("merchant") or clean_row.get("store") or clean_row.get("category") or "Store"
                city = clean_row.get("city") or clean_row.get("location") or clean_row.get("home_city") or "Bengaluru"
                home_city = clean_row.get("home_city") or city
                txn_status = clean_row.get("txn_status") or clean_row.get("status") or "success"

                lat_val = clean_row.get("lat") or clean_row.get("merch_lat") or clean_row.get("latitude")
                lon_val = clean_row.get("lon") or clean_row.get("merch_long") or clean_row.get("longitude")
                lat = float(lat_val) if (lat_val and str(lat_val).strip() != "") else None
                lon = float(lon_val) if (lon_val and str(lon_val).strip() != "") else None

                payload = {
                    "user_id": str(user_id),
                    "amount": amount,
                    "merchant": str(merchant),
                    "city": str(city),
                    "home_city": str(home_city),
                    "lat": lat,
                    "lon": lon,
                    "txn_status": str(txn_status),
                }
                avg_amt_key = clean_row.get("user_avg_amount_inr") or clean_row.get("user_avg_amount") or clean_row.get("avg_amount")
                if avg_amt_key:
                    try:
                        payload["user_avg_amount_inr"] = float(avg_amt_key)
                    except (ValueError, TypeError):
                        pass

                ts_key = clean_row.get("timestamp") or clean_row.get("time") or clean_row.get("date")
                if ts_key:
                    payload["timestamp"] = ts_key

                try:
                    process_transaction(payload, socketio=socketio)
                except Exception as exc:
                    logger.warning("[replay] Row error: %s", exc)

                _replay_state["processed"] += 1
                time.sleep(0.05)  # slight delay for smooth stream into UI

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
