"""
import_dataset.py — Import and evaluate your own custom / Kaggle dataset for fraud anomalies.

Works out-of-the-box with Kaggle datasets:
  • Credit Card Fraud Detection (ULB: Time, Amount, Class)
  • Sparkov Fraud Dataset (trans_date_trans_time, cc_num, amt, merchant, lat, long, is_fraud)
  • PaySim (step, type, amount, nameOrig, nameDest, isFraud)
  • Custom CSV datasets

Usage:
  python import_dataset.py --file path/to/kaggle_data.csv
  python import_dataset.py --file path/to/kaggle_data.csv --limit 500 --stream --delay 0.1
"""
import argparse
import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from routes.transactions import process_transaction


def import_csv(file_path: str, stream: bool = False, delay: float = 0.1, limit: int = 1000):
    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        sys.exit(1)

    app = create_app()
    socketio = app.extensions.get("socketio") if stream else None

    print(f"\n📂 Loading dataset from: {file_path}")
    print(f"🔄 Mode: {'Real-Time WebSocket Stream' if stream else 'High-Speed Batch Evaluation'}")
    if limit:
        print(f"⚙️ Limit: Processing up to {limit} rows")
    print("-" * 75)

    counts = {"APPROVE": 0, "FLAG": 0, "BLOCK": 0}
    rules_fired = {}
    total = 0
    errors = 0

    has_ground_truth = False
    tp = fp = tn = fn = 0

    with app.app_context():
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, start=1):
                if limit and row_num > limit:
                    break

                clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k}
                try:
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
                    status = clean_row.get("status") or clean_row.get("txn_status") or "success"

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
                        "txn_status": str(status),
                    }
                    avg_amt_key = clean_row.get("user_avg_amount_inr") or clean_row.get("user_avg_amount") or clean_row.get("avg_amount")
                    if avg_amt_key:
                        payload["user_avg_amount_inr"] = float(avg_amt_key)

                    ts_key = clean_row.get("unix_time") or clean_row.get("trans_date_trans_time") or clean_row.get("timestamp") or clean_row.get("time") or clean_row.get("date")
                    if ts_key:
                        payload["timestamp"] = ts_key

                    res = process_transaction(payload, socketio=socketio)
                    decision = res["decision"]
                    score = res["risk_score"]
                    counts[decision] += 1
                    total += 1

                    for r in res.get("reasons", []):
                        r_name = r.get("rule", "unknown")
                        rules_fired[r_name] = rules_fired.get(r_name, 0) + 1

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

                    gt_str = ""
                    if is_actual_fraud is not None:
                        has_ground_truth = True
                        predicted_fraud = decision in ("FLAG", "BLOCK")

                        if is_actual_fraud and predicted_fraud:
                            tp += 1
                            gt_str = " | 🎯 TRUE FRAUD (Caught)"
                        elif not is_actual_fraud and predicted_fraud:
                            fp += 1
                            gt_str = " | ⚠️ False Alarm"
                        elif not is_actual_fraud and not predicted_fraud:
                            tn += 1
                            gt_str = " | ✓ Correct Normal"
                        elif is_actual_fraud and not predicted_fraud:
                            fn += 1
                            gt_str = " | 🚨 MISSED FRAUD"


                    symbol = "✅" if decision == "APPROVE" else "⚠️" if decision == "FLAG" else "🚫"
                    reasons_str = ", ".join(r["rule"] for r in res.get("reasons", [])) or "Clean"
                    print(f"Row {row_num:4d} | {symbol} {decision:<7} | Score: {score:3d} | ₹{amount:>8,.0f} | {city[:10]:<10} | {reasons_str}{gt_str}")

                    if stream and delay > 0:
                        time.sleep(delay)

                except Exception as exc:
                    from models import db
                    db.session.rollback()
                    errors += 1
                    print(f"Row {row_num:4d} | ❌ Error: {exc}")

    print("\n" + "=" * 75)
    print("📊 EVALUATION SUMMARY")
    print("=" * 75)
    print(f"Total Rows Evaluated: {total}")
    print(f"  • Approved:   {counts['APPROVE']:>4} ({counts['APPROVE'] / total * 100:.1f}%)" if total else 0)
    print(f"  • Flagged:    {counts['FLAG']:>4} ({counts['FLAG'] / total * 100:.1f}%)" if total else 0)
    print(f"  • Blocked:    {counts['BLOCK']:>4} ({counts['BLOCK'] / total * 100:.1f}%)" if total else 0)
    print(f"  • Errors:     {errors:>4}")

    if rules_fired:
        print("\nRule Triggers:")
        for rule, count in rules_fired.items():
            print(f"  - {rule:<25}: {count} triggers")

    if has_ground_truth:
        actual_frauds = tp + fn
        total_eval = tp + fp + tn + fn
        precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0.0
        accuracy = ((tp + tn) / total_eval * 100) if total_eval > 0 else 0.0

        print("\n" + "-" * 75)
        print("🎯 KAGGLE GROUND-TRUTH BENCHMARK REPORT")
        print("-" * 75)
        print(f"  • Total Actual Frauds in Sample: {actual_frauds}")
        print(f"  • Successfully Caught (TP):      {tp}")
        print(f"  • Missed Frauds (FN):            {fn}")
        print(f"  • False Alarms (FP):             {fp}")
        print(f"  • System Precision:              {precision:.1f}%")
        print(f"  • System Fraud Recall:           {recall:.1f}%")
        print(f"  • Overall System Accuracy:       {accuracy:.1f}%")

    print("=" * 75 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import Kaggle or custom dataset for fraud anomaly detection.")
    parser.add_argument("--file", "-f", required=True, help="Path to CSV dataset")
    parser.add_argument("--stream", "-s", action="store_true", help="Stream transactions to WebSocket dashboard in real time")
    parser.add_argument("--delay", "-d", type=float, default=0.1, help="Delay in seconds between transactions when streaming (default: 0.1)")
    parser.add_argument("--limit", "-l", type=int, default=1000, help="Max rows to process (default: 1000, 0 for all)")
    args = parser.parse_args()

    import_csv(args.file, stream=args.stream, delay=args.delay, limit=args.limit)
