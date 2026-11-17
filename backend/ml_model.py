"""
ml_model.py — Scikit-Learn IsolationForest for Fraud Anomaly Detection.

Compares unsupervised ML anomaly detection against deterministic rule-based scoring.
Features extracted per transaction:
  1. amount: Transaction amount in INR
  2. amount_ratio: Transaction amount / user.avg_amount
  3. hour_of_day: 0 to 23
  4. is_weekend: 0 or 1
  5. is_failed: 1 if previous/current status is failed else 0
"""
import logging
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier

logger = logging.getLogger(__name__)


class FraudMLDetector:
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=self.random_state,
            n_estimators=100,
        )
        self.is_fitted = False
        self._seed_default_model()

    def _extract_features(self, amount: float, avg_amount: float, timestamp: float, txn_status: str) -> list[float]:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        ratio = (amount / avg_amount) if avg_amount > 0 else 1.0
        is_weekend = 1.0 if dt.weekday() >= 5 else 0.0
        is_failed = 1.0 if txn_status == "failed" else 0.0
        return [float(amount), float(ratio), float(dt.hour), is_weekend, is_failed]

    def _seed_default_model(self):
        """Fit with a synthetic baseline of normal and occasional fraudulent patterns."""
        rng = np.random.RandomState(self.random_state)
        # Normal transactions: amount ~ 500 - 5000, ratio ~ 0.5 - 2.0, hour ~ 8 - 22, success
        n_normal = 200
        normal_amounts = rng.uniform(200, 4000, n_normal)
        normal_ratios = rng.uniform(0.3, 1.8, n_normal)
        normal_hours = rng.uniform(8, 22, n_normal)
        normal_weekends = rng.choice([0.0, 1.0], size=n_normal, p=[0.7, 0.3])
        normal_failed = rng.choice([0.0, 1.0], size=n_normal, p=[0.95, 0.05])
        X_normal = np.column_stack([normal_amounts, normal_ratios, normal_hours, normal_weekends, normal_failed])

        # Anomalous transactions: high amount, high ratio, odd hour, failed
        n_anom = 15
        anom_amounts = rng.uniform(20000, 100000, n_anom)
        anom_ratios = rng.uniform(5.0, 25.0, n_anom)
        anom_hours = rng.uniform(1, 5, n_anom)
        anom_weekends = rng.choice([0.0, 1.0], size=n_anom)
        anom_failed = rng.choice([0.0, 1.0], size=n_anom, p=[0.4, 0.6])
        X_anom = np.column_stack([anom_amounts, anom_ratios, anom_hours, anom_weekends, anom_failed])

        X = np.vstack([X_normal, X_anom])
        self.model.fit(X)
        self.is_fitted = True

    def fit_from_transactions(self, transactions: list, user_avg_map: dict):
        """Re-fit the model on actual historical transactions from the database."""
        if len(transactions) < 10:
            return  # keep default baseline if insufficient samples

        X = []
        for txn in transactions:
            avg_amount = user_avg_map.get(txn.user_id, 2000.0)
            ts = txn.timestamp.timestamp()
            X.append(self._extract_features(txn.amount, avg_amount, ts, txn.txn_status))

        X = np.array(X)
        self.model.fit(X)
        self.is_fitted = True
        logger.info("[ml] Fitted IsolationForest with %d historical transactions.", len(X))

    def predict(self, amount: float, avg_amount: float, timestamp: float, txn_status: str) -> dict:
        """
        Predict whether a transaction is an anomaly.
        Returns:
          {
            "is_anomaly": bool,
            "anomaly_score": float (0.0 to 1.0, higher = more anomalous),
            "ml_decision": "ANOMALY" | "NORMAL"
          }
        """
        features = np.array([self._extract_features(amount, avg_amount, timestamp, txn_status)])
        # decision_function returns negative values for anomalies, positive for normal
        raw_score = float(self.model.decision_function(features)[0])
        pred = int(self.model.predict(features)[0])  # -1 for outlier, 1 for inlier

        # Normalize score into [0, 1] range for visual comparison
        # Usually decision_function lies between -0.3 and 0.3
        normalized_score = float(np.clip(0.5 - (raw_score * 1.5), 0.0, 1.0))

        return {
            "is_anomaly": pred == -1,
            "anomaly_score": round(normalized_score * 100, 1),
            "raw_score": round(raw_score, 4),
            "ml_decision": "ANOMALY" if pred == -1 else "NORMAL",
        }


# Global singleton instance
ml_detector = FraudMLDetector()


class SupervisedFraudDetector:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.is_fitted = False
        self._seed_default_model()

    def _extract_features(self, amount: float, avg_amount: float, timestamp: float, txn_status: str) -> list[float]:
        from datetime import datetime, timezone
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        ratio = (amount / avg_amount) if avg_amount > 0 else 1.0
        is_weekend = 1.0 if dt.weekday() >= 5 else 0.0
        is_failed = 1.0 if txn_status == "failed" else 0.0
        return [float(amount), float(ratio), float(dt.hour), is_weekend, is_failed]

    def _seed_default_model(self):
        """Fit with labeled synthetic baseline (normal + fraud)."""
        rng = np.random.RandomState(42)
        # Normal transactions: 200 rows, label=0
        n_normal = 200
        normal_amounts = rng.uniform(200, 4000, n_normal)
        normal_ratios = rng.uniform(0.3, 1.8, n_normal)
        normal_hours = rng.uniform(8, 22, n_normal)
        normal_weekends = rng.choice([0.0, 1.0], size=n_normal, p=[0.7, 0.3])
        normal_failed = rng.choice([0.0, 1.0], size=n_normal, p=[0.95, 0.05])
        X_normal = np.column_stack([normal_amounts, normal_ratios, normal_hours, normal_weekends, normal_failed])
        y_normal = np.zeros(n_normal, dtype=int)

        # Fraud transactions: 40 rows, label=1
        n_fraud = 40
        fraud_amounts = rng.uniform(20000, 100000, n_fraud)
        fraud_ratios = rng.uniform(5.0, 25.0, n_fraud)
        fraud_hours = rng.uniform(1, 5, n_fraud)
        fraud_weekends = rng.choice([0.0, 1.0], size=n_fraud)
        fraud_failed = rng.choice([0.0, 1.0], size=n_fraud, p=[0.4, 0.6])
        X_fraud = np.column_stack([fraud_amounts, fraud_ratios, fraud_hours, fraud_weekends, fraud_failed])
        y_fraud = np.ones(n_fraud, dtype=int)

        X = np.vstack([X_normal, X_fraud])
        y = np.concatenate([y_normal, y_fraud])
        self.model.fit(X, y)
        self.is_fitted = True

    def fit_from_transactions(self, transactions: list, user_avg_map: dict):
        """Re-fit on actual labeled transactions (BLOCK=fraud, APPROVE=normal, skip FLAG)."""
        if len(transactions) < 10:
            return
        X, y = [], []
        for txn in transactions:
            if txn.decision == "FLAG":
                continue
            avg = user_avg_map.get(txn.user_id, 2000.0)
            ts = txn.timestamp.timestamp()
            X.append(self._extract_features(txn.amount, avg, ts, txn.txn_status))
            y.append(1 if txn.decision == "BLOCK" else 0)
        if len(X) < 10:
            return
        self.model.fit(np.array(X), np.array(y))
        self.is_fitted = True
        logger.info("[ml] Fitted RandomForestClassifier with %d labeled transactions.", len(X))

    def predict(self, amount: float, avg_amount: float, timestamp: float, txn_status: str) -> dict:
        features = np.array([self._extract_features(amount, avg_amount, timestamp, txn_status)])
        proba = float(self.model.predict_proba(features)[0][1])
        is_fraud = proba >= 0.5
        return {
            "is_fraud": is_fraud,
            "fraud_probability": round(proba * 100, 1),
            "rf_decision": "FRAUD" if is_fraud else "NORMAL",
        }


# Module-level singletons
rf_detector = SupervisedFraudDetector()


def compute_ml_metrics(transactions: list, user_avg_map: dict) -> dict:
    """
    Compute precision/recall/F1 for IsolationForest and RandomForest
    against ground-truth labels derived from rule-based decisions.
    FLAG rows are skipped (ambiguous ground truth).
    """
    labeled = [t for t in transactions if t.decision != "FLAG"]
    if len(labeled) < 10:
        return {"error": "Insufficient labeled data (need 10+ non-FLAG transactions)"}

    if_tp = if_fp = if_tn = if_fn = 0
    rf_tp = rf_fp = rf_tn = rf_fn = 0
    agreed = 0

    for txn in labeled:
        ground_truth = 1 if txn.decision == "BLOCK" else 0
        avg = user_avg_map.get(txn.user_id, 2000.0)
        ts = txn.timestamp.timestamp()

        if_res = ml_detector.predict(txn.amount, avg, ts, txn.txn_status)
        if_pred = 1 if if_res["is_anomaly"] else 0

        rf_res = rf_detector.predict(txn.amount, avg, ts, txn.txn_status)
        rf_pred = 1 if rf_res["is_fraud"] else 0

        if if_pred == rf_pred:
            agreed += 1

        # IF confusion
        if ground_truth == 1 and if_pred == 1:
            if_tp += 1
        elif ground_truth == 0 and if_pred == 1:
            if_fp += 1
        elif ground_truth == 0 and if_pred == 0:
            if_tn += 1
        else:
            if_fn += 1

        # RF confusion
        if ground_truth == 1 and rf_pred == 1:
            rf_tp += 1
        elif ground_truth == 0 and rf_pred == 1:
            rf_fp += 1
        elif ground_truth == 0 and rf_pred == 0:
            rf_tn += 1
        else:
            rf_fn += 1

    def _metrics(tp, fp, tn, fn):
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        return {
            "precision": round(p, 4),
            "recall": round(r, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn,
            "confusion_matrix": [[tn, fp], [fn, tp]],
        }

    total = len(transactions)
    n_labeled = len(labeled)
    agreement_rate = round(agreed / n_labeled * 100, 1) if n_labeled > 0 else 0.0

    return {
        "total": total,
        "labeled": n_labeled,
        "agreed": agreed,
        "agreement_rate": agreement_rate,
        "isolation_forest": _metrics(if_tp, if_fp, if_tn, if_fn),
        "random_forest": _metrics(rf_tp, rf_fp, rf_tn, rf_fn),
    }

