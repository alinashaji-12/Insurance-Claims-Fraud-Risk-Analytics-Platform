"""Dashboard summary stats."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.claim import Claim
from app.schemas.claim import StatsSummary

router = APIRouter(prefix="/stats", tags=["stats"])

HIGH_RISK_THRESHOLD = 60.0
FLAGGED_THRESHOLD = 35.0


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
