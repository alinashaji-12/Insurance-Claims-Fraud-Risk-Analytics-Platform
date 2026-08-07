"""Dashboard summary stats and model metrics."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.claim import Claim
from app.schemas.claim import ModelMetrics, StatsMetrics, StatsSummary

router = APIRouter(prefix="/stats", tags=["stats"])

HIGH_RISK_THRESHOLD = 60.0
FLAGGED_THRESHOLD = 35.0

_MODELS_DIR = (
    Path(__file__).resolve().parents[2] / "ml_training" / "models"
)
_FRAUD_METRICS = _MODELS_DIR / "fraud_model_metrics.json"
_ANOMALY_METRICS = _MODELS_DIR / "anomaly_model_metrics.json"


def _load_metrics_json(path: Path) -> ModelMetrics | None:
    if not path.is_file():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return None
        return ModelMetrics.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


@router.get("/summary", response_model=StatsSummary)
def stats_summary(db: Session = Depends(get_db)) -> StatsSummary:
    total = int(db.scalar(select(func.count()).select_from(Claim)) or 0)
    pending = int(
        db.scalar(
            select(func.count()).select_from(Claim).where(Claim.fraud_score.is_(None))
        )
        or 0
    )
    flagged = int(
        db.scalar(
            select(func.count())
            .select_from(Claim)
            .where(
                Claim.fraud_score.is_not(None),
                Claim.fraud_score >= FLAGGED_THRESHOLD,
            )
        )
        or 0
    )
    high_risk = int(
        db.scalar(
            select(func.count())
            .select_from(Claim)
            .where(
                Claim.fraud_score.is_not(None),
                Claim.fraud_score >= HIGH_RISK_THRESHOLD,
            )
        )
        or 0
    )
    avg = db.scalar(
        select(func.avg(Claim.fraud_score)).where(Claim.fraud_score.is_not(None))
    )
    fraud_label_count = int(
        db.scalar(
            select(func.count()).select_from(Claim).where(Claim.fraud_label.is_(True))
        )
        or 0
    )

    return StatsSummary(
        total_claims=total,
        flagged_count=flagged,
        high_risk_count=high_risk,
        avg_score=round(float(avg or 0.0), 2),
        fraud_label_count=fraud_label_count,
        pending_score_count=pending,
    )


@router.get("/metrics", response_model=StatsMetrics)
def stats_metrics() -> StatsMetrics:
    """Serve committed training metrics for the dashboard (no DB required)."""
    fraud = _load_metrics_json(_FRAUD_METRICS)
    anomaly = _load_metrics_json(_ANOMALY_METRICS)
    available = fraud is not None or anomaly is not None
    return StatsMetrics(
        fraud_model=fraud,
        anomaly_model=anomaly,
        available=available,
        message=None if available else "Model metrics files not found on server.",
    )
