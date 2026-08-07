# ClaimGuard AI

Insurance Claims Fraud & Risk Analytics Platform — hackathon submission.

## Overview

ClaimGuard AI helps insurance analysts:

- Review incoming claims with a computed fraud-risk score (0–100)
- Understand **why** a claim was flagged (rules + ML + anomaly explainability)
- Spot potential fraud rings via shared entities (phone, bank, address, VIN, repair shop)
- Upload a batch of claims (CSV) and get them scored instantly
- Drill into a single claim for full risk breakdown

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, Recharts, react-force-graph-2d |
| Backend | FastAPI, Pydantic v2, SQLAlchemy (SQLite → Postgres-ready) |
| ML | XGBoost, Isolation Forest, SMOTE, SHAP, NetworkX |

## Architecture

See [docs/architecture.md](docs/architecture.md) for scoring formula, API map, and model metrics.
See [docs/demo_script.md](docs/demo_script.md) for a 2–3 minute judge walkthrough.

## Dataset

Download **Vehicle Insurance Claim Fraud Detection** from Kaggle
(https://www.kaggle.com/datasets/shivamb/vehicle-claim-fraud-detection)
and save as:

```
backend/data/raw/claims.csv
```

The seed script validates required columns and fails loudly if the file is missing.

## Model metrics

Held-out test set (see `backend/ml_training/models/fraud_model_metrics.json`):

| Metric | Value |
|--------|-------|
| F1 | ~0.23 |
| ROC-AUC | ~0.81 |
| Precision | ~0.16 |
| Recall | ~0.42 |

Fraud is rare (~6%). ROC-AUC is the primary ranking metric for analyst triage.
Isolation Forest anomaly rate ≈ 6% (`anomaly_model_metrics.json`).

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+ (3.12+ also works)
- Dataset CSV at `backend/data/raw/claims.csv`

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
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Verify: http://localhost:8000/health → `{"status":"ok"}`  
Swagger: http://localhost:8000/docs

Optional (retrain models — already checked in as `.pkl` for demo speed):

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

## Deploy on Render

Full stack (FastAPI + Next.js) deploys via the Blueprint at [`render.yaml`](render.yaml).

**Quick path:** [Render Dashboard](https://dashboard.render.com) → **New** → **Blueprint** → connect this repo → **Apply**. That creates `claimguard-api` and `claimguard-web`.

See **[docs/deploy_render.md](docs/deploy_render.md)** for env vars, CORS, Postgres vs SQLite, free-tier caveats, and the **gitignored `.pkl` models** requirement.

## Environment

| File | Vars |
|------|------|
| `backend/.env.example` | `DATABASE_URL`, `ALLOWED_ORIGINS` |
| `frontend/.env.local.example` | `NEXT_PUBLIC_API_URL` |

Never commit real secrets. `.env` / `.env.local` are gitignored.

## API (Phase 8)

- `GET /claims?status=&min_score=&page=&page_size=`
- `GET /claims/{id}` — score breakdown + SHAP explanations
- `POST /claims/upload` — multipart CSV
- `GET /network/{claim_id}` — linked-claim graph
- `GET /stats/summary` — dashboard aggregates

## License

MIT
