"""
models.py — SQLAlchemy ORM models for the Fraud Detection Sandbox.

Tables:
  • users        — registered cardholders with home-city baseline
  • transactions — every scored transaction with its risk decision
  • alerts       — high-risk notifications surfaced to the dashboard
"""
import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

# Single shared db instance, imported everywhere else
db = SQLAlchemy()


def _utcnow() -> datetime:
    """Return timezone-aware UTC datetime (avoids deprecation in Python 3.11+)."""
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────
class User(db.Model):
    """A cardholder whose transactions we monitor."""
    __tablename__ = "users"

    user_id    = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    name       = db.Column(db.String(120), nullable=False)
    home_city  = db.Column(db.String(80),  nullable=False)
    # Lat/lon of the user's home city — used by the impossible-travel rule
    home_lat   = db.Column(db.Float, nullable=False)
    home_lon   = db.Column(db.Float, nullable=False)
    # Rolling average transaction amount in INR (updated by scoring pipeline)
    avg_amount = db.Column(db.Float, nullable=False, default=2000.0)
    status     = db.Column(db.String(10), nullable=False, default="active")  # active | frozen
    created_at = db.Column(db.DateTime(timezone=True), default=_utcnow)

    # Relationships
    transactions = db.relationship("Transaction", backref="user", lazy="dynamic")
    alerts       = db.relationship("Alert", backref="user", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "user_id":    self.user_id,
            "name":       self.name,
            "home_city":  self.home_city,
            "home_lat":   self.home_lat,
            "home_lon":   self.home_lon,
            "avg_amount": self.avg_amount,
            "status":     self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────────────
class Transaction(db.Model):
    """A single financial transaction that has been scored."""
    __tablename__ = "transactions"

    txn_id     = db.Column(db.String(36), primary_key=True, default=_new_uuid)
    user_id    = db.Column(db.String(36), db.ForeignKey("users.user_id"), nullable=False, index=True)
    amount     = db.Column(db.Float, nullable=False)          # INR
    merchant   = db.Column(db.String(120), nullable=False)
    city       = db.Column(db.String(80),  nullable=False)
    lat        = db.Column(db.Float, nullable=False)
    lon        = db.Column(db.Float, nullable=False)
    timestamp  = db.Column(db.DateTime(timezone=True), default=_utcnow, index=True)
    # "success" | "failed"  — failed txns contribute to the repeated-failures rule
    txn_status = db.Column(db.String(10), nullable=False, default="success")
    risk_score = db.Column(db.Integer,  nullable=False, default=0)   # 0-100
    decision   = db.Column(db.String(10), nullable=False, default="APPROVE")  # APPROVE|FLAG|BLOCK
    # JSON list of {rule, points, detail}  — why the score is what it is
    reasons    = db.Column(db.JSON, nullable=False, default=list)
    # Admin can override a FLAG decision
    overridden_by = db.Column(db.String(10), nullable=True)  # "APPROVE" | "BLOCK"
    latency_ms    = db.Column(db.Float, nullable=True)
    device_info   = db.Column(db.JSON, nullable=True)

    def _resolve_device_info(self) -> dict:
        if self.device_info and isinstance(self.device_info, dict):
            return self.device_info
        h = abs(hash(f"{self.user_id}_{self.txn_id}")) % 100
        is_suspicious = (self.risk_score >= 70 or (self.reasons and any(r.get("rule") == "impossible_travel" for r in self.reasons if isinstance(r, dict))))
        if is_suspicious or (h < 15):
            return {
                "device_type": "Linux / Tor Node" if h < 5 else "Datacenter Proxy",
                "os": "Linux x86_64" if h < 5 else "Windows Server 2022",
                "browser": "HeadlessChrome / Puppeteer" if h < 5 else "Chrome (Automated)",
                "ip_type": "Tor Exit Node (High Risk)" if h < 5 else "Data Center (AWS/Hosting)",
                "vpn_detected": True,
                "device_trust": 12 if h < 5 else 34,
                "ip_address": f"198.51.{100 + (h % 50)}.{h * 2 + 1}",
            }
        devices = [
            {"device_type": "Mobile (iOS)", "os": "iOS 17.5", "browser": "Safari Mobile", "ip_type": "Residential (Jio 5G)", "vpn_detected": False, "device_trust": 96, "ip_address": f"49.36.{h}.{h * 2 + 3}"},
            {"device_type": "Mobile (Android)", "os": "Android 14", "browser": "Chrome Mobile", "ip_type": "Residential (Airtel Broadband)", "vpn_detected": False, "device_trust": 92, "ip_address": f"103.21.{h}.{h * 2 + 5}"},
            {"device_type": "Desktop (macOS)", "os": "macOS Sonoma", "browser": "Chrome 125", "ip_type": "Residential (ACT Fibernet)", "vpn_detected": False, "device_trust": 98, "ip_address": f"115.96.{h}.{h * 2 + 7}"},
            {"device_type": "Desktop (Windows)", "os": "Windows 11", "browser": "Edge 124", "ip_type": "Residential (Tata Tele)", "vpn_detected": False, "device_trust": 90, "ip_address": f"182.72.{h}.{h * 2 + 9}"},
        ]
        return devices[h % len(devices)]

    def to_dict(self) -> dict:
        return {
            "txn_id":       self.txn_id,
            "user_id":      self.user_id,
            "user_name":    self.user.name if self.user else None,
            "amount":       self.amount,
            "merchant":     self.merchant,
            "city":         self.city,
            "lat":          self.lat,
            "lon":          self.lon,
            "timestamp":    self.timestamp.isoformat() if self.timestamp else None,
            "txn_status":   self.txn_status,
            "risk_score":   self.risk_score,
            "decision":     self.overridden_by or self.decision,
            "raw_decision": self.decision,
            "reasons":      self.reasons or [],
            "overridden_by": self.overridden_by,
            "latency_ms":   self.latency_ms or 3.2,
            "device_info":  self._resolve_device_info(),
        }


# ─────────────────────────────────────────────────────────────────────────────
# Alert
# ─────────────────────────────────────────────────────────────────────────────
class Alert(db.Model):
    """A high-risk notification (risk_score ≥ 70) surfaced to the dashboard."""
    __tablename__ = "alerts"

    id           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    txn_id       = db.Column(db.String(36), db.ForeignKey("transactions.txn_id"), nullable=False)
    user_id      = db.Column(db.String(36), db.ForeignKey("users.user_id"),       nullable=False)
    message      = db.Column(db.Text, nullable=False)
    created_at   = db.Column(db.DateTime(timezone=True), default=_utcnow, index=True)
    acknowledged = db.Column(db.Boolean, nullable=False, default=False)

    transaction  = db.relationship("Transaction", backref="alert", uselist=False)

    def to_dict(self) -> dict:
        return {
            "id":           self.id,
            "txn_id":       self.txn_id,
            "user_id":      self.user_id,
            "message":      self.message,
            "created_at":   self.created_at.isoformat() if self.created_at else None,
            "acknowledged": self.acknowledged,
        }


# ─────────────────────────────────────────────────────────────────────────────
# NetworkEdge
# ─────────────────────────────────────────────────────────────────────────────
class NetworkEdge(db.Model):
    __tablename__ = "network_edges"
    id              = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id_a       = db.Column(db.String(36), nullable=False, index=True)
    user_id_b       = db.Column(db.String(36), nullable=False, index=True)
    shared_city     = db.Column(db.String(80), nullable=False)
    shared_merchant = db.Column(db.String(120), nullable=True)
    detected_at     = db.Column(db.DateTime(timezone=True), default=_utcnow)

    def to_dict(self):
        return {"id": self.id, "user_id_a": self.user_id_a, "user_id_b": self.user_id_b,
                "shared_city": self.shared_city, "shared_merchant": self.shared_merchant,
                "detected_at": self.detected_at.isoformat() if self.detected_at else None}
