# 📘 Fraud Detection Sandbox — Backend REST API Specification

Comprehensive developer reference for the Algorithmic Fraud Detection Sandbox API.

---

## 1. Core Transaction Scoring

### `POST /api/transaction`
Score and store a single real-time financial transaction.

**Request Body:**
```json
{
  "user_id": "U-3001",
  "amount": 45000.0,
  "merchant": "Apple Store Indiranagar",
  "city": "Bengaluru",
  "lat": 12.9716,
  "lon": 77.5946,
  "txn_status": "success",
  "device_info": {
    "device_type": "Mobile (iOS)",
    "ip_address": "49.36.12.8",
    "vpn_detected": false
  }
}
```

**Response (HTTP 201 Created):**
```json
{
  "txn_id": "0a19ee00-d849-487a-a314-c77f82996416",
  "decision": "APPROVE",
  "risk_score": 15,
  "latency_ms": 3.2,
  "reasons": [],
  "device_info": {
    "device_type": "Mobile (iOS)",
    "os": "iOS 17.5",
    "browser": "Safari Mobile",
    "ip_type": "Residential (Jio 5G)",
    "vpn_detected": false,
    "device_trust": 96
  }
}
```

---

## 2. Policy Backtesting & What-If Studio

### `POST /api/backtest`
Simulates rule parameter modifications against historical database records.

**Request Body:**
```json
{
  "speed_threshold_kmh": 800,
  "amount_multiplier": 2.5,
  "max_txns": 4,
  "window_seconds": 120,
  "approve_max": 35,
  "flag_max": 65,
  "sample_limit": 500
}
```

**Response (HTTP 200 OK):**
```json
{
  "status": "success",
  "total_evaluated": 500,
  "baseline": { "approved": 420, "flagged": 50, "blocked": 30, "fraud_rate": 16.0 },
  "simulated": { "approved": 395, "flagged": 65, "blocked": 40, "fraud_rate": 21.0 },
  "impact": {
    "fraud_interception_delta_pct": 5.0,
    "additional_blocks": 10,
    "additional_flags": 15,
    "recommendation": "🟢 Optimal Policy Balance: Stable risk containment with controlled customer friction."
  }
}
```

---

## 3. Graph Link Analysis (Mule Rings)

### `GET /api/rings`
Detects collusion clusters where multiple distinct accounts converge on shared merchant terminals or high-velocity mule corridors.

**Response (HTTP 200 OK):**
```json
{
  "rings": [
    {
      "merchant": "Crypto Exchange Terminal 04",
      "user_count": 4,
      "total_amount": 185000.0,
      "users": ["U-102", "U-109", "U-115", "U-144"]
    }
  ],
  "graph": {
    "nodes": [...],
    "edges": [...]
  }
}
```

---

## 4. Sandbox Reset & Ingestion

### `POST /api/reset`
Wipes all transactions, alerts, and edges while preserving baseline user accounts for clean re-testing.

**Response (HTTP 200 OK):**
```json
{
  "status": "success",
  "message": "Database reset complete. 58 users retained (all active, avg_amount reset). 0 transactions, 0 alerts, 0 network edges.",
  "users_retained": 58
}
```

---

## 5. System Health & Telemetry

### `GET /api/health`
Health check for container orchestrators and load balancers.

### `GET /api/telemetry`
Engine performance metrics, SLA compliance stats, and active heuristic configurations.
