# 🛡️ Algorithmic Fraud Detection Sandbox

An end-to-end, real-time financial transaction scoring and fraud detection sandbox designed for demonstration and educational purposes. The system evaluates simulated transactions in real time and makes automated **APPROVE / FLAG / BLOCK** decisions before settlement, backed by a live reactive dashboard and an unsupervised Machine Learning benchmark (Isolation Forest).

---

## 🌟 Highlights & Architecture

```
                    ┌────────────────────────┐
                    │  Transaction Simulator │
                    │ (Normal + Attack Inject)│
                    └───────────┬────────────┘
                                │ HTTP / WebSocket
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                      Flask Backend API                       │
 │  ┌────────────────────────────────────────────────────────┐  │
 │  │                Scoring & Decision Engine               │  │
 │  │  • Impossible Travel (Haversine km/h > 800)            │  │
 │  │  • Velocity Limit (> 3 txns / 60s)                     │  │
 │  │  • Amount Anomaly (3x user average or Z-Score > 3.0)   │  │
 │  │  • Repeated Failures (3 fails / 15m → Freeze Account)  │  │
 │  └────────────────────────┬───────────────────────────────┘  │
 │                           │                                  │
 │   ┌───────────────────────┼──────────────────────┐           │
 │   ▼                       ▼                      ▼           │
 │ [Postgres / SQLite]  [Redis / Dict Cache]  [Isolation Forest] │
 └───────────────┬──────────────────────────────────────┬───────┘
                 │ WebSocket (`socket.io`)              │ REST API
                 ▼                                      ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                      React + Vite UI                         │
 │  • Real-time Live Feed & Score Breakdown                     │
 │  • KPI Summary Cards & Chart.js Visualizations               │
 │  • Slide-in Transaction Audit & Rule Explanations            │
 │  • Admin User Freeze & Manual Override Controls              │
 │  • Live Threshold Configuration Drawer                       │
 │  • Rules vs IsolationForest (ML) Benchmark Tab               │
 └──────────────────────────────────────────────────────────────┘
```

- **Dual-Mode Persistence**: Uses PostgreSQL when configured, or automatically falls back to SQLite (`fraud.db`) for zero-configuration, instant execution on any laptop.
- **Resilient Caching**: Connects to Redis for high-speed location and velocity tracking; gracefully degrades to a thread-safe in-memory cache if Redis is absent.
- **Rule Engine + ML Comparison**: Combines deterministic multi-rule scoring with scikit-learn's unsupervised **IsolationForest** anomaly detector.
- **Full WebSocket Integration**: Emits real-time transaction updates, high-risk alerts, and live aggregation metrics to the frontend via Socket.IO.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+ (with npm)
- *(Optional)* **Docker & Docker Compose** (for PostgreSQL + Redis)

---

### 2. Backend Setup

```bash
# Navigate to the backend directory
cd backend

# Create and activate a Python virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Seed the database with sample users and historical profiles
python seed.py

# Run the Flask backend server (port 5001)
python app.py
```
> The backend server will start on `http://localhost:5001`.

---

### 3. Frontend Setup

In a new terminal window:

```bash
# Navigate to the frontend directory
cd frontend

# Install npm packages
npm install

# Start the Vite development server
npm run dev
```
> The dashboard will be available at `http://localhost:5173`.

---

### 4. (Optional) Run with Docker (PostgreSQL + Redis)

If you wish to run dedicated PostgreSQL and Redis containers:

```bash
# In the project root:
docker-compose up -d
```
The backend automatically detects and connects to Redis (`localhost:6379`) and PostgreSQL (`localhost:5432`) when available.

---

## 🧪 Running Automated Tests

Run the complete test suite (21 unit and integration tests covering rules, pipeline scoring, and ML models):

```bash
cd backend
source venv/bin/activate
pytest -v
```

---

## 📊 Live System Walkthrough & College Presentation Script

Use this 5-step walkthrough to impress professors or evaluators during a demo:

### Step 1: Normal Transaction Traffic
1. Open `http://localhost:5173` in your browser.
2. In the **Simulator Controls** bar at the top, click **▶ Start Simulator**.
3. Point out how transactions stream in via WebSockets in real time:
   - Amounts in Indian Rupees (₹).
   - Dynamic Risk Scores (0–100).
   - Decisions: Mostly green **APPROVE** badges for everyday shopping.
   - Live updates to the **Decision Split Doughnut** and **Rule Trigger Bar Chart**.

### Step 2: Injecting Attack Patterns
Demonstrate how the fraud engine immediately catches malicious behavior using the 4 injection buttons:
- **⚡ Velocity Burst**: Fires 5 transactions within seconds. Watch the **Velocity Limit** rule trigger and turn decisions to **FLAG / BLOCK**.
- **🚀 Impossible Travel**: Simulates a transaction in Bengaluru followed 2 minutes later by Guwahati (over 2,000 km away). Demonstrates speed calculation exceeding 800 km/h.
- **💰 Amount Spike**: Injects an anomalous ₹85,000 transaction for a user with an average spend of ₹1,500.
- **🔒 Repeated Failures**: Simulates 3 consecutive PIN/CVV failures, automatically freezing the customer's account to protect funds.

### Step 3: Transaction Explainability (Audit Trail)
1. Click any row in the **Live Feed Table**.
2. A slide-in right drawer opens, showing the **Scoring Breakdown**:
   - Exact rule triggers (e.g. `+40 pts: Velocity exceeded 3 txns in 60s`).
   - Total accumulated risk score and resulting threshold tier.
   - Full transaction metadata (coordinates, timestamp, merchant).

### Step 4: Admin Controls & Dynamic Rules
1. Navigate to the **Admin** tab:
   - View seeded users, account statuses, and average spending profiles.
   - Manually **Freeze** or **Unfreeze** accounts.
   - Review **Flagged Transactions** and perform manual human-in-the-loop overrides (**Approve** or **Block**).
2. Click **⚙ Settings** in the top navigation bar:
   - Adjust rule thresholds on the fly (e.g., lower max travel speed from 800 to 500 km/h).
   - Changes take effect immediately without restarting the server!

### Step 5: Machine Learning vs Rules Benchmark
1. Switch to the **🤖 ML Benchmark** tab:
   - Highlights the comparison between deterministic heuristics and unsupervised **Isolation Forest**.
   - Displays the **Agreement Rate**, **High-Confidence Overlaps**, and discrepancies.
   - Demonstrates how unsupervised ML catches subtle multidimensional outliers without explicit rule definitions.
   - Click **🔄 Retrain Model** to showcase retraining on current database records.

---

## 🛠️ API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/transaction` | Score, record, and broadcast a transaction |
| `GET` | `/api/transactions` | Query transaction history (supports `?decision=FLAG` & `?limit=50`) |
| `POST` | `/api/transactions/<id>/override` | Override a decision (`APPROVE` or `BLOCK`) |
| `GET` | `/api/stats` | Aggregated dashboard metrics & rule trigger counts |
| `GET` | `/api/users` | List users and their account states |
| `POST` | `/api/users/<id>/freeze` | Freeze a user account |
| `POST` | `/api/users/<id>/unfreeze` | Unfreeze a user account |
| `GET` | `/api/config` | View current live rule thresholds |
| `PUT` | `/api/config` | Update rule thresholds in memory |
| `POST` | `/api/simulator/start` | Start background simulated transactions |
| `POST` | `/api/simulator/stop` | Pause simulated transactions |
| `POST` | `/api/simulator/inject` | Inject specific fraud patterns |
| `GET` | `/api/ml/compare` | Evaluate transactions against IsolationForest ML |
| `POST` | `/api/ml/retrain` | Retrain IsolationForest model on active transactions |

---

## 📁 Repository Structure

```
fraud-sandbox/
├── backend/
│   ├── app.py                # Flask application factory & WebSocket setup
│   ├── config.py             # Config settings & default rule thresholds
│   ├── models.py             # SQLAlchemy models (User, Transaction, Alert)
│   ├── redis_store.py        # Redis client with graceful in-memory fallback
│   ├── scoring.py            # Rule evaluation & decision pipeline
│   ├── ml_model.py           # IsolationForest ML anomaly detector
│   ├── seed.py               # Seed script with realistic Indian users & cities
│   ├── simulator.py          # Background transaction simulator & fraud generator
│   ├── routes/               # API route blueprints
│   ├── rules/                # Independent rule modules (travel, velocity, etc.)
│   └── tests/                # 21 unit & integration pytest tests
├── frontend/
│   ├── src/
│   │   ├── components/       # 10 UI components (Feed, Charts, Admin, ML, etc.)
│   │   ├── api.js            # REST API client
│   │   ├── socket.js         # Socket.IO WebSocket singleton
│   │   ├── index.css         # Modern dark-mode design system & animations
│   │   └── App.jsx           # Root layout and state orchestration
│   ├── package.json
│   └── vite.config.js        # Vite config with backend proxy
├── docker-compose.yml        # PostgreSQL 15 + Redis 7 services
└── README.md
```

---

## 🎓 College Submission Notes
- **Subject**: Financial Technology / Information Security / Web Engineering
- **Focus**: Real-time Stream Scoring, Fraud Heuristics, HA Architecture (in-memory fallbacks), Unsupervised ML Comparison, Explainable AI.
