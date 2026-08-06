"""Pydantic v2 schemas for claims API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class RuleHitSchema(BaseModel):
    rule_id: str
    points: float
    reason: str


class ScoreComponents(BaseModel):
    rules_score: float
    rules_weighted: float
    ml_probability: float
    ml_weighted: float
    anomaly_flag: bool
    anomaly_score: float
    anomaly_weighted: float


class ExplanationItem(BaseModel):
    feature: str
    importance: float
    shap_value: float
    reason: str


class ClaimSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    policy_number: str
    claimant_name: str
    claim_type: str
    claim_amount: float
    incident_date: date
    fraud_score: Optional[float] = None
    fraud_label: Optional[bool] = None
    status: str
    repair_shop: str
    submitted_at: datetime


class ClaimDetail(ClaimSummary):
    claimant_phone: str
    claimant_address: str
    bank_account: str
    vehicle_vin: str
    description: str
    age: Optional[int] = None
    vehicle_category: Optional[str] = None
    vehicle_price_band: Optional[str] = None
    accident_area: Optional[str] = None
    fault: Optional[str] = None
    past_number_of_claims: Optional[str] = None
    police_report_filed: Optional[str] = None
    witness_present: Optional[str] = None
    days_policy_claim: Optional[str] = None
    address_change_claim: Optional[str] = None
    make: Optional[str] = None
    score_breakdown: Optional[ScoreComponents] = None
    rule_hits: list[RuleHitSchema] = Field(default_factory=list)
    explanations: list[ExplanationItem] = Field(default_factory=list)
    weights: Optional[dict[str, float]] = None


class ClaimsListResponse(BaseModel):
    items: list[ClaimSummary]
    total: int
    page: int
    page_size: int


class UploadResultItem(BaseModel):
    row_number: int
    policy_number: str
    claimant_name: str
    claim_amount: float
    fraud_score: float
    status: str
    claim_id: Optional[int] = None
    error: Optional[str] = None


class UploadResponse(BaseModel):
    accepted: int
    rejected: int
    results: list[UploadResultItem]
    errors: list[str] = Field(default_factory=list)


class NetworkNode(BaseModel):
    id: int
    claim_id: int
    label: str
    fraud_score: Optional[float] = None
    policy_number: Optional[str] = None
    is_focus: bool = False


class NetworkEdge(BaseModel):
    source: int
    target: int
    shared_entities: list[dict[str, Any]] = Field(default_factory=list)


class NetworkRing(BaseModel):
    claim_ids: list[int]
    size: int


class NetworkResponse(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    rings: list[NetworkRing]
    focus_claim_id: Optional[int] = None


class StatsSummary(BaseModel):
    total_claims: int
    flagged_count: int
    high_risk_count: int
    avg_score: float
    fraud_label_count: int
    pending_score_count: int
