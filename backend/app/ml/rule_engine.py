"""
Business rule engine for insurance claim fraud signals.

Each rule returns a weighted point value and a human-readable reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RuleHit:
    rule_id: str
    points: float
    reason: str


@dataclass(frozen=True)
class RuleResult:
    score: float  # 0–100 scale contribution before weighting
    hits: list[RuleHit]
    max_possible: float


# Percentile thresholds can be injected from dataset stats
DEFAULT_AMOUNT_P90_BY_TYPE: dict[str, float] = {
    "Liability": 25000.0,
    "Collision": 22000.0,
    "All Perils": 28000.0,
}


def _get(claim: Mapping[str, Any], key: str, default: Any = None) -> Any:
    return claim.get(key, default)


def rule_early_claim(claim: Mapping[str, Any]) -> RuleHit | None:
    """Claim filed very soon after policy start (Days_Policy_Claim = none / short)."""
    days = str(_get(claim, "days_policy_claim", "") or "").lower()
    if days in {"none", "1 to 7", "8 to 15"}:
        return RuleHit(
            rule_id="early_claim",
            points=18.0,
            reason=f"Claim filed unusually soon after policy start (days_policy_claim={days}).",
        )
    return None


def rule_high_amount(claim: Mapping[str, Any], p90_by_type: Mapping[str, float]) -> RuleHit | None:
    claim_type = str(_get(claim, "claim_type") or _get(claim, "base_policy") or "Unknown")
    amount = float(_get(claim, "claim_amount", 0) or 0)
    p90 = float(p90_by_type.get(claim_type, 25000.0))
    if amount > p90:
        ratio = amount / p90 if p90 else 0
        return RuleHit(
            rule_id="high_amount",
            points=min(25.0, 12.0 + ratio * 4.0),
            reason=(
                f"Claim amount ${amount:,.0f} exceeds the 90th percentile "
                f"(${p90:,.0f}) for {claim_type} claims ({ratio:.1f}x)."
            ),
        )
    return None


def rule_round_amount(claim: Mapping[str, Any]) -> RuleHit | None:
    amount = float(_get(claim, "claim_amount", 0) or 0)
    if amount >= 1000 and amount % 1000 == 0:
        return RuleHit(
            rule_id="round_amount",
            points=8.0,
            reason=f"Claim amount ${amount:,.0f} is a round number, which is statistically uncommon.",
        )
    return None


def rule_no_police_report(claim: Mapping[str, Any]) -> RuleHit | None:
    report = str(_get(claim, "police_report_filed", "") or "").lower()
    amount = float(_get(claim, "claim_amount", 0) or 0)
    if report == "no" and amount > 10000:
        return RuleHit(
            rule_id="no_police_report",
            points=12.0,
            reason=(
                f"No police report filed on a higher-value claim (${amount:,.0f})."
            ),
        )
    return None


def rule_no_witness(claim: Mapping[str, Any]) -> RuleHit | None:
    witness = str(_get(claim, "witness_present", "") or "").lower()
    fault = str(_get(claim, "fault", "") or "").lower()
    if witness == "no" and "policy holder" in fault:
        return RuleHit(
            rule_id="no_witness_at_fault",
            points=10.0,
            reason="Policy holder at fault with no witness present.",
        )
    return None


def rule_address_change(claim: Mapping[str, Any]) -> RuleHit | None:
    change = str(_get(claim, "address_change_claim", "") or "").lower()
    if change in {"under 6 months", "1 year"}:
        return RuleHit(
            rule_id="recent_address_change",
            points=14.0,
            reason=f"Recent address change relative to claim ({change}).",
        )
    return None


def rule_many_past_claims(claim: Mapping[str, Any]) -> RuleHit | None:
    past = str(_get(claim, "past_number_of_claims", "") or "").lower()
    if past in {"more than 4", "2 to 4"}:
        points = 16.0 if past == "more than 4" else 9.0
        return RuleHit(
            rule_id="past_claims",
            points=points,
            reason=f"Elevated prior claim history ({past}).",
        )
    return None


def rule_young_driver_expensive(claim: Mapping[str, Any]) -> RuleHit | None:
    age = _get(claim, "age")
    price_band = str(_get(claim, "vehicle_price_band", "") or "").lower()
    if age is not None and int(age) < 25 and "more than 69000" in price_band:
        return RuleHit(
            rule_id="young_expensive_vehicle",
            points=11.0,
            reason=f"Young driver (age {age}) with high-value vehicle band ({price_band}).",
        )
    return None


def rule_mismatch_area_shop(claim: Mapping[str, Any]) -> RuleHit | None:
    """Heuristic: rural accident but urban-sounding repair shop name pattern."""
    area = str(_get(claim, "accident_area", "") or "").lower()
    shop = str(_get(claim, "repair_shop", "") or "").lower()
    urban_markers = ("metro", "city", "downtown", "urban")
    if area == "rural" and any(m in shop for m in urban_markers):
        return RuleHit(
            rule_id="area_shop_mismatch",
            points=10.0,
            reason=(
                f"Rural accident area but repair shop '{_get(claim, 'repair_shop')}' "
                "looks urban — possible staging / shop collusion signal."
            ),
        )
    return None


def evaluate_rules(
    claim: Mapping[str, Any],
    amount_p90_by_type: Mapping[str, float] | None = None,
) -> RuleResult:
    """Run all rules and return aggregated points (capped at 100) + reasons."""
    p90 = amount_p90_by_type or DEFAULT_AMOUNT_P90_BY_TYPE
    hits: list[RuleHit] = []

    checks: Sequence[RuleHit | None] = [
        rule_early_claim(claim),
        rule_high_amount(claim, p90),
        rule_round_amount(claim),
        rule_no_police_report(claim),
        rule_no_witness(claim),
        rule_address_change(claim),
        rule_many_past_claims(claim),
        rule_young_driver_expensive(claim),
        rule_mismatch_area_shop(claim),
    ]
    for hit in checks:
        if hit is not None:
            hits.append(hit)

    raw = sum(h.points for h in hits)
    max_possible = 18 + 25 + 8 + 12 + 10 + 14 + 16 + 11 + 10  # theoretical max
    score = min(100.0, raw)
    return RuleResult(score=score, hits=hits, max_possible=float(max_possible))


def claim_model_to_mapping(claim: Any) -> dict[str, Any]:
    """Convert a SQLAlchemy Claim (or similar object) to a plain mapping."""
    keys = [
        "policy_number",
        "claimant_name",
        "claimant_phone",
        "claimant_address",
        "bank_account",
        "vehicle_vin",
        "incident_date",
        "claim_type",
        "claim_amount",
        "description",
        "repair_shop",
        "submitted_at",
        "age",
        "vehicle_category",
        "vehicle_price_band",
        "accident_area",
        "fault",
        "past_number_of_claims",
        "age_of_vehicle",
        "police_report_filed",
        "witness_present",
        "base_policy",
        "days_policy_claim",
        "address_change_claim",
        "deductible",
        "driver_rating",
        "sex",
        "make",
    ]
    if isinstance(claim, Mapping):
        return {k: claim.get(k) for k in keys}
    return {k: getattr(claim, k, None) for k in keys}
