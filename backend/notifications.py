from datetime import datetime, timezone


class NotificationService:
    def __init__(self):
        self._log = []

    def _entry(self, type_, msg, **extra):
        e = {"type": type_, "message": msg, "timestamp": datetime.now(timezone.utc).isoformat(), **extra}
        self._log.append(e)
        print(f"[NOTIFY] {msg}")
        return e

    def send_fraud_alert(self, user_name, txn_id, decision, amount, city, risk_score):
        return self._entry(
            "fraud_alert",
            f"🚨 FRAUD ALERT: {user_name} | txn {txn_id[:8]} | {decision} | ₹{amount:,.0f} in {city} | Risk: {risk_score}",
            user_name=user_name,
            txn_id=txn_id,
        )

    def send_account_frozen(self, user_name, user_id):
        return self._entry(
            "account_frozen",
            f"🔒 ACCOUNT FROZEN: {user_name} (ID: {user_id})",
            user_name=user_name,
            user_id=user_id,
        )

    def send_otp_challenge(self, user_name, user_id, txn_id):
        return self._entry(
            "otp_challenge",
            f"📱 OTP CHALLENGE sent to {user_name} for txn {txn_id[:8]}",
            user_name=user_name,
            user_id=user_id,
            txn_id=txn_id,
        )

    def get_log(self, limit=50):
        return list(reversed(self._log))[:limit]

    def clear_log(self):
        self._log.clear()
        return True


notification_service = NotificationService()
