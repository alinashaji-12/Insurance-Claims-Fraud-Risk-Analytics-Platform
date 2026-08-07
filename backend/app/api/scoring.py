"""Shared scoring helpers used by API routes and batch jobs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.explain import explain_claim
from app.ml.fraud_model import compute_composite_score
from app.models.claim import Claim
from app.schemas.claim import (
    ClaimDetail,
    ExplanationItem,
    RuleHitSchema,
    ScoreComponents,
)


def score_and_persist(
    claim: Claim, db: Session, *, persist: bool = True
) -> dict[str, Any]:
    result = compute_composite_score(claim)
    claim.fraud_score = result["fraud_score"]
    if result["fraud_score"] >= 60:
        claim.status = "flagged"
    elif result["fraud_score"] >= 35:
        claim.status = "review"
    else:
        claim.status = "open"
    if persist:
        db.add(claim)
        db.commit()
        db.refresh(claim)
    return result


def build_claim_detail(claim: Claim, *, with_explanation: bool = True) -> ClaimDetail:
    result = compute_composite_score(claim)
    explanations: list[ExplanationItem] = []
    if with_explanation:
        explanations = [ExplanationItem(**e) for e in explain_claim(claim, top_k=5)]

    return ClaimDetail(
        id=claim.id,
        policy_number=claim.policy_number,
        claimant_name=claim.claimant_name,
        claimant_phone=claim.claimant_phone,
        claimant_address=claim.claimant_address,
        bank_account=claim.bank_account,
        vehicle_vin=claim.vehicle_vin,
        incident_date=claim.incident_date,
        claim_type=claim.claim_type,
        claim_amount=claim.claim_amount,
        description=claim.description,
        repair_shop=claim.repair_shop,
        submitted_at=claim.submitted_at,
        fraud_score=result["fraud_score"],
        fraud_label=claim.fraud_label,
        status=claim.status,
        age=claim.age,
        vehicle_category=claim.vehicle_category,
        vehicle_price_band=claim.vehicle_price_band,
        accident_area=claim.accident_area,
        fault=claim.fault,
        past_number_of_claims=claim.past_number_of_claims,
        police_report_filed=claim.police_report_filed,
        witness_present=claim.witness_present,
        days_policy_claim=claim.days_policy_claim,
        address_change_claim=claim.address_change_claim,
        make=claim.make,
        score_breakdown=ScoreComponents(**result["components"]),
        rule_hits=[RuleHitSchema(**h) for h in result["rule_hits"]],
        explanations=explanations,
        weights=result["weights"],
    )


def get_claim_or_none(db: Session, claim_id: int) -> Claim | None:
    return db.get(Claim, claim_id)


def list_all_claims(db: Session) -> list[Claim]:
    return list(db.scalars(select(Claim)).all())
