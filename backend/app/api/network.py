"""Fraud network graph endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.api.scoring import get_claim_or_none
from app.core.database import get_db
from app.ml.fraud_network import build_network_payload
from app.models.claim import Claim
from app.schemas.claim import NetworkResponse

router = APIRouter(prefix="/network", tags=["network"])


def _claims_for_network(db: Session, focus: Claim) -> list[Claim]:
    """
    Load focus claim plus candidates that may share entities.

    Avoids building a 15k-node graph on every request while still catching rings.
    """
    filters = [
        Claim.claimant_phone == focus.claimant_phone,
        Claim.bank_account == focus.bank_account,
        Claim.claimant_address == focus.claimant_address,
        Claim.vehicle_vin == focus.vehicle_vin,
        Claim.repair_shop == focus.repair_shop,
    ]
    related = list(db.scalars(select(Claim).where(or_(*filters)).limit(500)).all())
    by_id = {c.id: c for c in related}
    by_id[focus.id] = focus

    # Always include demo fraud-ring claims so visualization stays demo-ready
    demo = list(
        db.scalars(
            select(Claim).where(
                or_(
                    Claim.policy_number.like("RING-ALPHA%"),
                    Claim.policy_number.like("RING-BETA%"),
                )
            )
        ).all()
    )
    for c in demo:
        by_id[c.id] = c

    return list(by_id.values())


@router.get("/{claim_id}", response_model=NetworkResponse)
def get_claim_network(claim_id: int, db: Session = Depends(get_db)) -> NetworkResponse:
    claim = get_claim_or_none(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")

    claims = _claims_for_network(db, claim)
    payload = build_network_payload(claims, focus_claim_id=claim_id)
    return NetworkResponse(**payload)
