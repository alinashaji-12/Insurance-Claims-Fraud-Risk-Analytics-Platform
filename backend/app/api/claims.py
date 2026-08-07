"""Claims list, detail, and CSV upload endpoints."""

from __future__ import annotations

import io

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.scoring import build_claim_detail, get_claim_or_none, score_and_persist
from app.core.database import get_db
from app.models.claim import Claim
from app.schemas.claim import (
    ClaimDetail,
    ClaimsListResponse,
    ClaimSummary,
    UploadResponse,
    UploadResultItem,
)
from app.seed import REQUIRED_COLUMNS, SIMPLE_REQUIRED, row_to_claim, simple_row_to_claim

router = APIRouter(prefix="/claims", tags=["claims"])


@router.get("", response_model=ClaimsListResponse)
def list_claims(
    status: str | None = Query(None, description="Filter by status"),
    min_score: float | None = Query(
        None, ge=0, le=100, description="Minimum fraud score"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
) -> ClaimsListResponse:
    query = select(Claim)
    count_query = select(func.count()).select_from(Claim)

    if status:
        query = query.where(Claim.status == status)
        count_query = count_query.where(Claim.status == status)
    if min_score is not None:
        query = query.where(
            Claim.fraud_score.is_not(None), Claim.fraud_score >= min_score
        )
        count_query = count_query.where(
            Claim.fraud_score.is_not(None), Claim.fraud_score >= min_score
        )

    total = int(db.scalar(count_query) or 0)
    offset = (page - 1) * page_size
    # Prefer higher scores first; unscored last (SQLite-safe null ordering)
    score_null_rank = case((Claim.fraud_score.is_(None), 1), else_=0)
    query = query.order_by(
        score_null_rank.asc(), Claim.fraud_score.desc(), Claim.id.asc()
    )
    claims = list(db.scalars(query.offset(offset).limit(page_size)).all())

    # Lazy-score the current page so the demo UI is never empty of scores.
    # Soft-fail: missing/broken ML artifacts must not block the entire list.
    for claim in claims:
        if claim.fraud_score is None:
            try:
                score_and_persist(claim, db, persist=True)
            except Exception:  # noqa: BLE001
                db.rollback()

    items = [ClaimSummary.model_validate(c) for c in claims]
    return ClaimsListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int, db: Session = Depends(get_db)) -> ClaimDetail:
    claim = get_claim_or_none(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    try:
        score_and_persist(claim, db, persist=True)
        return build_claim_detail(claim, with_explanation=True)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail=f"Scoring unavailable: {exc}",
        ) from exc


@router.post("/upload", response_model=UploadResponse)
async def upload_claims(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload must be a .csv file")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded CSV is empty")

    try:
        df = pd.read_csv(io.BytesIO(raw), comment="#")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400, detail=f"Failed to parse CSV: {exc}"
        ) from exc

    if df.empty:
        raise HTTPException(status_code=400, detail="CSV has no data rows")

    columns = set(df.columns)
    is_kaggle = "PolicyNumber" in columns

    # Normalize simple-format column names to lowercase
    if not is_kaggle:
        df.columns = [str(c).strip().lower() for c in df.columns]
        missing = SIMPLE_REQUIRED - set(df.columns)
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    "CSV is missing required columns: "
                    + ", ".join(sorted(missing))
                    + ". Expected either the Kaggle dataset schema or: "
                    + ", ".join(sorted(SIMPLE_REQUIRED))
                ),
            )
    else:
        missing = REQUIRED_COLUMNS - columns
        if missing:
            raise HTTPException(
                status_code=400,
                detail="Kaggle CSV is missing required columns: "
                + ", ".join(sorted(missing)),
            )

    results: list[UploadResultItem] = []
    errors: list[str] = []
    accepted = 0
    rejected = 0

    for idx, row in df.iterrows():
        row_number = int(idx) + 2  # header is row 1
        try:
            claim = row_to_claim(row) if is_kaggle else simple_row_to_claim(row)
            db.add(claim)
            db.flush()
            score_result = score_and_persist(claim, db, persist=True)
            accepted += 1
            results.append(
                UploadResultItem(
                    row_number=row_number,
                    policy_number=claim.policy_number,
                    claimant_name=claim.claimant_name,
                    claim_amount=claim.claim_amount,
                    fraud_score=float(score_result["fraud_score"]),
                    status=claim.status,
                    claim_id=claim.id,
                )
            )
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            rejected += 1
            msg = f"Row {row_number}: {exc}"
            errors.append(msg)
            policy = str(row.get("policy_number") or row.get("PolicyNumber") or "")
            name = str(row.get("claimant_name") or "")
            try:
                amount = float(row.get("claim_amount") or 0)
            except (TypeError, ValueError):
                amount = 0.0
            results.append(
                UploadResultItem(
                    row_number=row_number,
                    policy_number=policy,
                    claimant_name=name,
                    claim_amount=amount,
                    fraud_score=0.0,
                    status="error",
                    error=str(exc),
                )
            )

    return UploadResponse(
        accepted=accepted,
        rejected=rejected,
        results=results,
        errors=errors,
    )
