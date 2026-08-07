# ClaimGuard AI — Demo Script (≈2–3 minutes)

## Setup before judges walk up

1. Backend running: `uvicorn app.main:app --reload --port 8000`
2. Frontend running: `npm run dev` → http://localhost:3000
3. Seed already loaded (`python -m app.seed` once) so the queue is never empty

## Walkthrough

### 0:15 — Open the dashboard

- Open **ClaimGuard AI** home.
- Point to summary cards: total claims, high-risk count, average score.
- Say: *“Every claim gets a 0–100 composite risk score from business rules, an XGBoost model trained on a real Kaggle vehicle-fraud dataset, and an Isolation Forest anomaly detector.”*

### 0:45 — Filter / sort the queue

- Set **Min score** to `35` or sort by score.
- Click a mid/high-risk claim (not a demo ring yet).
- Say: *“Analysts can triage by score and status instead of reading every claim cold.”*

### 1:15 — Explainability on a claim

On the detail page:

1. Show the **weighted contribution chart** (Rules / ML / Anomaly).
2. Read 1–2 **plain-English reasons** (rule hits + SHAP phrases).
3. Say: *“Judges care about why — not just a black-box number. SHAP turns model features into readable drivers.”*

### 1:45 — Fraud ring

- From the dashboard search or open claim id for policy `RING-ALPHA-01`
  (or any `RING-ALPHA-*` / `RING-BETA-*` demo claim).
- Show the **fraud network** graph with 3+ linked nodes.
- Say: *“Edges mean shared phone, bank, address, or VIN — classic fraud-ring signals. We inject a tiny demo ring because the public CSV has unique entities per row.”*

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
