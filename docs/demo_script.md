# ClaimGuard AI — Demo Script (≈2–3 minutes)

## Setup before judges walk up

1. Backend running: `uvicorn app.main:app --reload --port 8000`
2. Frontend running: `npm run dev` → http://localhost:3000
3. Empty DB auto-seeds on API start (`claims_demo.csv` + `RING-*` fraud rings, scored at seed).
   Full Kaggle seed is optional: `python -m app.seed`

## Walkthrough

### 0:15 — Open the dashboard

- Open **ClaimGuard AI** home.
- Point to summary cards: total claims, **High risk** (should be > 0), **Flagged / review**, average score.
- Glance at the **Model metrics** strip (ROC-AUC ≈ 0.81).
- Say: *“Every claim gets a 0–100 composite risk score from business rules, an XGBoost model trained on a real Kaggle vehicle-fraud dataset, and an Isolation Forest anomaly detector.”*

### 0:45 — Filter / sort the queue

- Set **Min score** to `35` or sort by score.
- Click a mid/high-risk claim that is **not** a fraud-ring badge yet (e.g. `DEMO-023` or `DEMO-007`).
- Say: *“Analysts can triage by score and status instead of reading every claim cold.”*

### 1:15 — Explainability on a claim

On the detail page:

1. Show the **weighted contribution chart** (Rules / ML / Anomaly).
2. Read 1–2 **plain-English reasons** (rule hits + SHAP phrases).
3. Say: *“Judges care about why — not just a black-box number. SHAP turns model features into readable drivers.”*

### 1:45 — Fraud ring (exact click path)

1. Back to the dashboard.
2. Click **Show fraud rings** (or search `RING-ALPHA-01`).
3. Open the row with policy **`RING-ALPHA-01`** (badge: Fraud ring).
4. Scroll to the **fraud network** graph — you should see 3+ linked nodes (RING-ALPHA cluster).
5. Say: *“Edges mean shared phone, bank, address, or VIN — classic fraud-ring signals. We inject RING-ALPHA / RING-BETA because the public CSV has unique entities per row.”*

Optional: also open `RING-BETA-01` for the second ring.

### 2:15 — Bulk upload (optional if time)

- Go to **Bulk Upload**.
- Drop a valid simple CSV (or the sample you prepared).
- Show scored rows returning immediately.
- Optionally drop a broken CSV (missing columns) and show the clear error — not a crash.

### 2:45 — Close

- *“Real dataset, real model metrics (ROC-AUC ≈ 0.81), explainability, and ring detection — ready for analyst triage.”*

## Talking points if asked

- **Why F1 is modest:** class imbalance (~6% fraud); we optimize triage ranking (ROC-AUC) and human review, not perfect precision.
- **Weights:** 35% rules / 45% ML / 20% anomaly — transparent and tunable.
- **Postgres later:** change `DATABASE_URL` only; models stay the same.
- **Cold start:** if the dashboard shows “API waking up”, hit **Retry** — Render free tier can take 30–60s.
