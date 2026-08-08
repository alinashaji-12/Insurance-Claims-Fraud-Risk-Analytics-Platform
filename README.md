# ClaimGuard AI

**Insurance Claims Fraud & Risk Analytics Platform** — triage vehicle claims with a 0–100 risk score, explainable ML, and fraud-ring network detection.

## Live demo

| Surface | URL |
|---------|-----|
| Web app | https://claimguard-web.onrender.com |
| API health | https://claimguard-api-ruwo.onrender.com/health |

**Demo tip:** Render free-tier services sleep when idle. Open the [API `/health`](https://claimguard-api-ruwo.onrender.com/health) endpoint first (wait until `{"status":"ok"}`), then load the web app. On the dashboard, click **Show fraud rings** and open policy **`RING-ALPHA-01`** for the network graph.

Judge walkthrough: [docs/demo_script.md](docs/demo_script.md).

## Features

- **Risk scoring** — composite 0–100 score from business rules, XGBoost fraud model, and Isolation Forest anomaly detection
- **Explainability** — rule hits plus SHAP-backed plain-English drivers on each claim
- **Fraud rings** — shared-entity graph (phone, bank, address, VIN, repair shop) with demo rings (`RING-ALPHA-*`, `RING-BETA-*`)
- **Analyst queue** — filter/sort by score and status; search by policy or claimant
- **Bulk upload** — CSV ingest with immediate scoring
- **Model metrics** — ROC-AUC and related stats surfaced on the dashboard
- **Auto demo seed** — empty DB loads a small demo CSV + fraud rings on API start

## Tech stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, Recharts, react-force-graph-2d |
| Backend | FastAPI, Pydantic v2, SQLAlchemy (SQLite locally; Postgres-ready) |
| ML | XGBoost, Isolation Forest, SMOTE, SHAP, NetworkX |
| Deploy | Render Blueprint (`render.yaml`) — FastAPI + Next.js |

## Architecture

Claims flow through a hybrid scorer: **35% rules / 45% ML / 20% anomaly**, producing a triage score and explanations. Linked claims form a network via shared entities for ring detection.

Details (scoring formula, API map, model notes): [docs/architecture.md](docs/architecture.md).

## Model metrics

Held-out test set (`backend/ml_training/models/fraud_model_metrics.json`):

| Metric | Value |
|--------|-------|
| F1 | ≈ 0.23 |
| ROC-AUC | ≈ 0.81 |
| Precision | ≈ 0.16 |
| Recall | ≈ 0.42 |
| Accuracy | ≈ 0.83 |

Fraud is rare (~6%). **ROC-AUC** is the primary ranking metric for analyst triage; modest F1 is expected under class imbalance. Isolation Forest anomaly rate ≈ 6% (`anomaly_model_metrics.json`).

## Dataset

Primary training / seed source: [Vehicle Insurance Claim Fraud Detection](https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection) (Kaggle).

For full local seed, save the CSV as:

```text
backend/data/raw/claims.csv
```

The seed script validates required columns and fails loudly if the file is missing. Deployed demos use the committed `backend/data/demo/claims_demo.csv` plus synthetic fraud-ring rows when the DB is empty.

## Local setup

### Prerequisites

- Node.js 18+
- Python 3.11+ (3.12+ also works)
- Optional: full Kaggle CSV at `backend/data/raw/claims.csv` (otherwise rely on demo auto-seed)

### Backend

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Optional full seed (requires claims.csv):
# python -m app.seed
uvicorn app.main:app --reload --port 8000
```

- Health: http://localhost:8000/health → `{"status":"ok"}`
- Swagger: http://localhost:8000/docs

Optional retrain (models are already checked in as `.pkl` for demo speed):

```bash
python -m ml_training.train_fraud_model
python -m ml_training.train_anomaly_model
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
# NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

Open http://localhost:3000

### Environment variables

| File | Variables |
|------|-----------|
| `backend/.env.example` | `DATABASE_URL`, `ALLOWED_ORIGINS` |
| `frontend/.env.local.example` | `NEXT_PUBLIC_API_URL` |

Never commit real secrets. `.env` / `.env.local` are gitignored.

## Deploy on Render

Full stack deploys via the Blueprint at [`render.yaml`](render.yaml).

**Quick path:** [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** → connect this repo → **Apply**. Creates `claimguard-api` and `claimguard-web`.

Step-by-step (env vars, CORS, Postgres vs SQLite, cold starts): **[docs/deploy_render.md](docs/deploy_render.md)**.

## Project structure

```text
.
├── backend/
│   ├── app/                 # FastAPI routes, scoring, seed, ORM
│   ├── data/
│   │   ├── demo/            # Small demo CSV for auto-seed
│   │   └── raw/             # Place full Kaggle CSV here
│   ├── ml_training/         # Train scripts + model artifacts / metrics
│   └── tests/
├── frontend/
│   ├── app/                 # Next.js App Router pages
│   ├── components/          # UI (queue, charts, network graph)
│   └── lib/                 # API client, helpers
├── docs/                    # Architecture, deploy, demo script
├── render.yaml              # Render Blueprint
└── README.md
```

## License

MIT
