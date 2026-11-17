"""
routes/transactions.py — Transaction submission, batch import, CSV upload, retrieval, and admin override.

Endpoints:
  POST /api/transaction              Score & store a single transaction
  POST /api/transactions/batch       Score & store a batch of JSON transactions
  POST /api/transactions/upload-csv  Upload and score a CSV dataset
  GET  /api/transactions             List transactions (filterable)
  POST /api/transactions/<id>/override  Admin: approve or block a flagged txn
"""
import csv
import io
import time
import logging
from datetime import datetime, timezone

from flask import Blueprint, request, jsonify, current_app

from models import db, Transaction, User, Alert
from scoring import score_transaction

logger = logging.getLogger(__name__)
txn_bp = Blueprint("transactions", __name__, url_prefix="/api")

CITY_COORDS = {
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "hyderabad": (17.3850, 78.4867),
    "chennai": (13.0827, 80.2707),
    "kolkata": (22.5726, 88.3639),
    "pune": (18.5204, 73.8567),
    "ahmedabad": (23.0225, 72.5714),
    "jaipur": (26.9124, 75.7873),
    "guwahati": (26.1445, 91.7362),
    "lucknow": (26.8467, 80.9462),
    "kochi": (9.9312, 76.2673),
    "chandigarh": (30.7333, 76.7794),
}


def _broadcast(socketio, event: str, data: dict):
    """Emit a WebSocket event (silently ignore if socketio not yet wired)."""
    try:
        socketio.emit(event, data)
    except Exception as exc:
        logger.warning("[ws] Could not emit %s: %s", event, exc)


def _get_or_create_user(user_id: str, city: str = "Bengaluru", lat: float = None, lon: float = None, amount: float = 2000.0, avg_amount: float = None) -> User:
    """Get existing user or auto-create/update one for imported datasets."""
    user = User.query.get(user_id)
    target_avg = avg_amount if (avg_amount is not None and avg_amount > 0) else max(float(amount), 500.0)
    if not user:
        if lat is None or lon is None:
            coords = CITY_COORDS.get((city or "").lower().strip(), (12.9716, 77.5946))
            lat, lon = coords
        user = User(
            user_id=str(user_id),
            name=f"Customer {str(user_id)[:8]}",
            home_city=city or "Bengaluru",
            home_lat=float(lat),
            home_lon=float(lon),
            avg_amount=target_avg,
            status="active"
        )
        db.session.add(user)
        db.session.commit()
        logger.info("[user] Auto-created user %s for dataset import.", user_id)
    elif avg_amount is not None and abs(user.avg_amount - avg_amount) > 0.01:
        user.avg_amount = avg_amount
        db.session.commit()
    return user


def process_transaction(data: dict, socketio=None) -> dict:
    """
    Validate, score, persist, and broadcast a transaction.
    Returns the serialised transaction dict.
    Raises ValueError for bad input.
    """
    amount_raw = (
        data.get("amount") or
        data.get("amount_inr") or
        data.get("amt") or
        data.get("amt_inr") or
        data.get("trans_amount") or
        data.get("price") or
        data.get("val")
    )
    if amount_raw is None:
        for k, v in data.items():
            if "amount" in k.lower() or k.lower() == "amt":
                amount_raw = v
                break

    if amount_raw is None:
        raise ValueError("Missing required field: amount")

    amount = float(amount_raw)
    if amount <= 0:
        raise ValueError("amount must be positive")

    user_id = str(data.get("user_id") or "user_default")
    city = str(data.get("city") or "Bengaluru")
    home_city = str(data.get("home_city") or city)
    merchant = str(data.get("merchant") or "Generic Merchant")
    txn_status = str(data.get("txn_status") or data.get("status") or "success").lower()

    if txn_status not in ("success", "failed"):
        txn_status = "success"

    # Resolve lat/lon if missing
    lat = data.get("lat")
    lon = data.get("lon")
    if lat is None or lon is None or str(lat).strip() == "" or str(lon).strip() == "":
        coords = CITY_COORDS.get(city.lower().strip(), (12.9716, 77.5946))
        lat, lon = coords
    else:
        lat = float(lat)
        lon = float(lon)

    # Resolve timestamp
    ts_val = data.get("timestamp")
    if ts_val is not None:
        try:
            ts = float(ts_val)
        except (ValueError, TypeError):
            try:
                ts = datetime.fromisoformat(str(ts_val).strip()).timestamp()
            except Exception:
                try:
                    ts = datetime.strptime(str(ts_val).strip(), "%Y-%m-%d %H:%M:%S").timestamp()
                except Exception:
                    ts = time.time()
    else:
        ts = time.time()

    avg_amt_raw = (
        data.get("user_avg_amount_inr") or
        data.get("user_avg_amount") or
        data.get("avg_amount") or
        data.get("avg_amount_inr")
    )
    user_avg = float(avg_amt_raw) if avg_amt_raw is not None else None

    user = _get_or_create_user(user_id, city=home_city, lat=lat, lon=lon, amount=amount, avg_amount=user_avg)


    # ── Score ─────────────────────────────────────────────────────────────────
    rule_config = current_app.config["RULE_CONFIG"]
    result = score_transaction(
        user=user,
        amount=amount,
        lat=lat,
        lon=lon,
        city=city,
        txn_id="temp",
        txn_status=txn_status,
        timestamp=ts,
        rule_config=rule_config,
    )

    # ── Persist transaction ───────────────────────────────────────────────────
    txn = Transaction(
        user_id    = user.user_id,
        amount     = amount,
        merchant   = merchant,
        city       = city,
        lat        = lat,
        lon        = lon,
        timestamp  = datetime.fromtimestamp(ts, tz=timezone.utc),
        txn_status = txn_status,
        risk_score = result.score,
        decision   = result.decision,
        reasons    = result.reasons,
    )
    db.session.add(txn)

    # ── Freeze account if signalled ───────────────────────────────────────────
    if result.freeze_account and user.status != "frozen":
        user.status = "frozen"
        logger.info("[scoring] User %s (%s) frozen due to repeated failures.", user.user_id, user.name)

    db.session.commit()

    # ── Create high-risk alert ────────────────────────────────────────────────
    alert_data = None
    if result.score >= 70:
        msg = (
            f"⚠️ {result.decision}: {user.name} — ₹{amount:,.0f} at {merchant}, {city}. "
            f"Score: {result.score}/100."
        )
        alert = Alert(txn_id=txn.txn_id, user_id=user.user_id, message=msg)
        db.session.add(alert)
        db.session.commit()
        alert_data = alert.to_dict()

    txn_dict = txn.to_dict()

    # ── Broadcast via WebSocket ───────────────────────────────────────────────
    if socketio is None:
        socketio = current_app.extensions.get("socketio")
    if socketio:
        _broadcast(socketio, "new_transaction", txn_dict)
        if alert_data:
            _broadcast(socketio, "new_alert", alert_data)

    return txn_dict


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@txn_bp.route("/transaction", methods=["POST"])
def post_transaction():
    """Score and store a new transaction."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    try:
        result = process_transaction(data)
        return jsonify(result), 201
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    except Exception as exc:
        logger.error("[POST /api/transaction] Unexpected error: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error"}), 500


@txn_bp.route("/transactions/batch", methods=["POST"])
def post_batch_transactions():
    """Score and store an array of transactions."""
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify({"error": "Request body must be a JSON array of transactions"}), 400

    results = []
    errors = []
    counts = {"APPROVE": 0, "FLAG": 0, "BLOCK": 0}

    for idx, item in enumerate(data):
        try:
            res = process_transaction(item)
            counts[res["decision"]] = counts.get(res["decision"], 0) + 1
            results.append(res)
        except Exception as exc:
            errors.append({"index": idx, "error": str(exc)})

    return jsonify({
        "total_processed": len(results),
        "total_errors": len(errors),
        "counts": counts,
        "errors": errors,
        "sample_results": results[:10],
    }), 201


@txn_bp.route("/transactions/upload-csv", methods=["POST"])
def upload_csv():
    """
    Upload and evaluate a custom CSV dataset.
    Accepts:
      - Multipart file named 'file'
      - OR text/csv raw body
    Query params:
      - stream=true: Emit each transaction live via WebSockets
    """
    stream = request.args.get("stream", "false").lower() == "true"
    limit = int(request.args.get("limit", 500))  # default 500 rows to prevent HTTP timeout
    if limit <= 0:
        limit = 5000

    csv_text = None
    if "file" in request.files:
        uploaded_file = request.files["file"]
        csv_text = uploaded_file.read().decode("utf-8", errors="replace")
    elif request.data:
        csv_text = request.data.decode("utf-8", errors="replace")

    if not csv_text or not csv_text.strip():
        return jsonify({"error": "No CSV data provided"}), 400

    reader = csv.DictReader(io.StringIO(csv_text))
    processed = []
    errors = []
    counts = {"APPROVE": 0, "FLAG": 0, "BLOCK": 0}

    # Ground truth tracking (for Kaggle datasets containing is_fraud or Class)
    has_ground_truth = False
    tp = fp = tn = fn = 0

    socketio = current_app.extensions.get("socketio") if stream else None

    for row_num, row in enumerate(reader, start=1):
        if row_num > limit:
            break
        clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
        try:
            # Flexible amount mapping (supports amount_inr, amt_inr, amount, price, etc.)
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
            amount = float(amount_val or 0)

            user_id = clean_row.get("user_id") or clean_row.get("cc_num") or clean_row.get("nameorig") or clean_row.get("customer_id") or clean_row.get("card_id") or f"cust_{row_num}"
            merchant = clean_row.get("merchant") or clean_row.get("namedest") or clean_row.get("category") or clean_row.get("store") or "Store"
            city = clean_row.get("city") or clean_row.get("location") or clean_row.get("state") or "Bengaluru"
            home_city = clean_row.get("home_city") or city
            txn_status = clean_row.get("status") or clean_row.get("txn_status") or "success"

            lat_val = clean_row.get("lat") or clean_row.get("merch_lat") or clean_row.get("latitude")
            lon_val = clean_row.get("lon") or clean_row.get("long") or clean_row.get("merch_long") or clean_row.get("longitude")
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
                payload["user_avg_amount_inr"] = float(avg_amt_key)

            ts_key = clean_row.get("unix_time") or clean_row.get("trans_date_trans_time") or clean_row.get("timestamp") or clean_row.get("time") or clean_row.get("date")
            if ts_key:
                payload["timestamp"] = ts_key

            res = process_transaction(payload, socketio=socketio)
            counts[res["decision"]] = counts.get(res["decision"], 0) + 1
            processed.append(res)

            # Check for Kaggle / custom ground truth
            is_actual_fraud = None
            if clean_row.get("is_fraud") is not None or clean_row.get("isfraud") is not None or clean_row.get("class") is not None:
                gt_val = clean_row.get("is_fraud") or clean_row.get("isfraud") or clean_row.get("class")
                is_actual_fraud = str(gt_val).strip() in ("1", "true", "True", "fraud", "yes")
            elif clean_row.get("decision") is not None and clean_row.get("decision").strip() in ("APPROVE", "FLAG", "BLOCK"):
                is_actual_fraud = clean_row.get("decision").strip().upper() in ("FLAG", "BLOCK")
            elif clean_row.get("scenario") is not None:
                sc = clean_row.get("scenario").strip().lower()
                is_actual_fraud = sc not in ("normal", "clean", "legit")

            if is_actual_fraud is not None:
                has_ground_truth = True
                predicted_fraud = res["decision"] in ("FLAG", "BLOCK")

                if is_actual_fraud and predicted_fraud:
                    tp += 1
                elif not is_actual_fraud and predicted_fraud:
                    fp += 1
                elif not is_actual_fraud and not predicted_fraud:
                    tn += 1
                elif is_actual_fraud and not predicted_fraud:
                    fn += 1

        except Exception as exc:
            db.session.rollback()
            errors.append({"row": row_num, "error": str(exc)})


    resp_data = {
        "total_rows_evaluated": len(processed),
        "total_errors": len(errors),
        "counts": counts,
        "errors": errors[:5],
        "message": f"Successfully evaluated {len(processed)} transactions from dataset."
    }

    if has_ground_truth:
        actual_frauds = tp + fn
        total_eval = tp + fp + tn + fn
        precision = round((tp / (tp + fp) * 100), 1) if (tp + fp) > 0 else 0.0
        recall = round((tp / (tp + fn) * 100), 1) if (tp + fn) > 0 else 0.0
        accuracy = round(((tp + tn) / total_eval * 100), 1) if total_eval > 0 else 0.0
        resp_data["kaggle_evaluation"] = {
            "has_ground_truth": True,
            "actual_frauds_in_sample": actual_frauds,
            "detected_frauds": tp,
            "missed_frauds": fn,
            "false_alarms": fp,
            "precision_pct": precision,
            "recall_pct": recall,
            "accuracy_pct": accuracy,
        }

    return jsonify(resp_data), 200


@txn_bp.route("/transactions", methods=["GET"])
def list_transactions():
    """List transactions with optional filters."""
    decision = request.args.get("decision")
    user_id  = request.args.get("user_id")
    limit    = min(int(request.args.get("limit", 50)), 200)

    q = Transaction.query.order_by(Transaction.timestamp.desc())
    if decision:
        q = q.filter(Transaction.decision == decision.upper())
    if user_id:
        q = q.filter(Transaction.user_id == user_id)

    txns = q.limit(limit).all()
    return jsonify([t.to_dict() for t in txns])


@txn_bp.route("/transactions/<txn_id>/override", methods=["POST"])
def override_transaction(txn_id: str):
    """Admin endpoint: override a transaction decision."""
    txn = Transaction.query.get(txn_id)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404

    data   = request.get_json(silent=True) or {}
    action = str(data.get("action", "")).upper()
    if action not in ("APPROVE", "BLOCK"):
        return jsonify({"error": "action must be 'APPROVE' or 'BLOCK'"}), 422

    txn.overridden_by = action
    db.session.commit()
    return jsonify(txn.to_dict())
