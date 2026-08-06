# ClaimGuard AI

Insurance Claims Fraud & Risk Analytics Platform — hackathon submission.

## Overview

ClaimGuard AI helps insurance analysts:

- Review incoming claims with a computed fraud-risk score (0–100)
- Understand **why** a claim was flagged (rule + ML + anomaly explainability)
- Spot potential fraud rings via shared entities (phone, bank, address, VIN, repair shop)
- Upload a batch CSV and get claims scored instantly

## Tech Stack

| Layer | Stack |
|-------|-------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind, shadcn/ui, Recharts |
| Backend | FastAPI, Pydantic v2, SQLAlchemy (SQLite → Postgres-ready) |
| ML | XGBoost, Isolation Forest, SMOTE, SHAP, NetworkX |

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+ (3.12+ also works)
- Kaggle dataset CSV placed at `backend/data/raw/claims.csv`

### Dataset

Download **Vehicle Insurance Claim Fraud Detection** (or Auto Insurance Claims Fraud Data) from Kaggle and save as:

```
backend/data/raw/claims.csv
```

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
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000

## Project Status

Scaffolding in progress — see phase commits for details.

## License

MIT
