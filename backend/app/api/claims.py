"""Claims list, detail, and CSV upload endpoints."""

from __future__ import annotations

import io
from datetime import date, datetime

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
from app.seed import REQUIRED_COLUMNS, row_to_claim

router = APIRouter(prefix="/claims", tags=["claims"])

# Simple analyst CSV (frontend bulk upload)
SIMPLE_REQUIRED = {
    "policy_number",
    "claimant_name",
    "claimant_phone",
    "claimant_address",
    "bank_account",
    "vehicle_vin",
    "incident_date",
    "claim_type",
    "claim_amount",
    "repair_shop",
}


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

    # Lazy-score the current page so the demo UI is never empty of scores
    for claim in claims:
        if claim.fraud_score is None:
            score_and_persist(claim, db, persist=True)

    items = [ClaimSummary.model_validate(c) for c in claims]
    return ClaimsListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: int, db: Session = Depends(get_db)) -> ClaimDetail:
    claim = get_claim_or_none(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    score_and_persist(claim, db, persist=True)
    return build_claim_detail(claim, with_explanation=True)


def _parse_simple_row(row: pd.Series, row_number: int) -> Claim:
    incident_raw = row["incident_date"]
    if isinstance(incident_raw, datetime):
        incident = incident_raw.date()
    elif isinstance(incident_raw, date):
        incident = incident_raw
    else:
        incident = date.fromisoformat(str(incident_raw).strip()[:10])

    submitted_raw = row.get("submitted_at")
    if (
        pd.isna(submitted_raw)
        or submitted_raw is None
        or str(submitted_raw).strip() == ""
    ):
        submitted = datetime.combine(incident, datetime.min.time()).replace(hour=10)
    elif isinstance(submitted_raw, datetime):
        submitted = submitted_raw
    else:
        submitted = datetime.fromisoformat(str(submitted_raw).strip().replace("Z", ""))

    def _opt_str(key: str) -> str | None:
        val = row.get(key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        text = str(val).strip()
        return text or None

    def _opt_int(key: str) -> int | None:
        val = row.get(key)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None

    return Claim(
        policy_number=str(row["policy_number"]).strip(),
        claimant_name=str(row["claimant_name"]).strip(),
        claimant_phone=str(row["claimant_phone"]).strip(),
        claimant_address=str(row["claimant_address"]).strip(),
        bank_account=str(row["bank_account"]).strip(),
        vehicle_vin=str(row["vehicle_vin"]).strip(),
        incident_date=incident,
        claim_type=str(row["claim_type"]).strip(),
        claim_amount=float(row["claim_amount"]),
        description=str(row.get("description") or "").strip(),
        repair_shop=str(row["repair_shop"]).strip(),
        submitted_at=submitted,
        fraud_score=None,
        fraud_label=None,
        status="pending",
        age=_opt_int("age"),
        vehicle_category=_opt_str("vehicle_category"),
        vehicle_price_band=_opt_str("vehicle_price_band"),
        accident_area=_opt_str("accident_area"),
        fault=_opt_str("fault"),
        past_number_of_claims=_opt_str("past_number_of_claims"),
        age_of_vehicle=_opt_str("age_of_vehicle"),
        police_report_filed=_opt_str("police_report_filed"),
        witness_present=_opt_str("witness_present"),
        base_policy=_opt_str("base_policy") or str(row["claim_type"]).strip(),
        days_policy_claim=_opt_str("days_policy_claim"),
        address_change_claim=_opt_str("address_change_claim"),
        deductible=_opt_int("deductible"),
        driver_rating=_opt_int("driver_rating"),
        sex=_opt_str("sex"),
        make=_opt_str("make"),
    )


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
            claim = (
                row_to_claim(row) if is_kaggle else _parse_simple_row(row, row_number)
            )
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
