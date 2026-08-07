# ClaimGuard AI — Architecture

## Overview

ClaimGuard AI is a hackathon-ready Insurance Claims Fraud & Risk Analytics platform.

- **Frontend:** Next.js 14 (App Router) + TypeScript + Tailwind + Recharts + react-force-graph-2d
- **Backend:** FastAPI + Pydantic v2 + SQLAlchemy (SQLite by default; swap `DATABASE_URL` for Postgres)
- **ML:** XGBoost (supervised), Isolation Forest (anomaly), SHAP (explainability), NetworkX (fraud rings)

```
CSV seed ──► SQLite claims
                 │
                 ▼
      Rule engine + XGBoost + Isolation Forest
                 │
                 ▼
         Composite fraud_score (0–100)
                 │
    ┌────────────┼────────────┐
    ▼            ▼            ▼
 Dashboard   Claim detail   CSV upload
             + SHAP reasons
             + network graph
```

## Scoring formula

Documented in `app/ml/fraud_model.py`:

```
fraud_score = 100 * (
  0.35 * rules_norm +
  0.45 * P(fraud)_xgboost +
  0.20 * anomaly_norm
)
```

Status bands:

| Score | Status  |
|-------|---------|
| ≥ 60  | flagged |
| ≥ 35  | review  |
| < 35  | open    |

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| GET | `/claims` | Paginated list (`status`, `min_score`, `page`, `page_size`) |
| GET | `/claims/{id}` | Detail + score breakdown + SHAP reasons |
| POST | `/claims/upload` | CSV upload + score |
| GET | `/network/{claim_id}` | Shared-entity neighborhood graph |
| GET | `/stats/summary` | Dashboard aggregates |

## Data

Primary training / seed source: Kaggle **Vehicle Insurance Claim Fraud Detection**
(Oracle dataset / `PolicyNumber`, `FraudFound_P`, etc.), placed at
`backend/data/raw/claims.csv`.

Demo fraud rings (`RING-ALPHA-*`, `RING-BETA-*`) are injected in `app/seed.py`
because the source CSV has no naturally shared phone/bank/VIN entities.

## Model metrics (held-out test)

From `backend/ml_training/models/fraud_model_metrics.json`:

| Metric | Value |
|--------|-------|
| F1 | ~0.23 |
| ROC-AUC | ~0.81 |
| Precision | ~0.16 |
| Recall | ~0.42 |

Imbalance is severe (~6% fraud). Accuracy alone is misleading; ROC-AUC shows
ranking quality suitable for analyst triage. Isolation Forest contamination ≈ 6%.
