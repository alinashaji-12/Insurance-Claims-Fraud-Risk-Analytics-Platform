"""
Fraud ML classifier inference + composite fraud score.

Composite formula (documented):
  fraud_score = 100 * (
      0.35 * rules_norm +
      0.45 * ml_probability +
      0.20 * anomaly_norm
  )

Where:
  - rules_norm     = rule_engine score / 100
  - ml_probability = P(fraud) from XGBoost
  - anomaly_norm   = 1.0 if IsolationForest flags anomaly else anomaly_score/100 * 0.5
                     (soft contribution even when not flagged)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

import joblib
import pandas as pd

from app.ml.anomaly_model import score_anomaly
from app.ml.rule_engine import RuleResult, claim_model_to_mapping, evaluate_rules

MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "ml_training" / "models" / "fraud_model.pkl"
)

# Composite weights — must sum to 1.0
WEIGHT_RULES = 0.35
WEIGHT_ML = 0.45
WEIGHT_ANOMALY = 0.20


@lru_cache
def load_fraud_artifact() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Fraud model not found at {MODEL_PATH}. "
            "Run ml_training/train_fraud_model.py first."
        )
    return joblib.load(MODEL_PATH)


def _claim_to_ml_row(claim: Mapping[str, Any]) -> pd.DataFrame:
    """Map ClaimGuard claim fields → original training column names."""
    return pd.DataFrame(
        [
            {
                "Age": claim.get("age") or 0,
                "Deductible": claim.get("deductible") or 400,
                "DriverRating": claim.get("driver_rating") or 1,
                "Sex": claim.get("sex") or "unknown",
                "MaritalStatus": "unknown",
                "Make": claim.get("make") or "unknown",
                "AccidentArea": claim.get("accident_area") or "unknown",
                "Fault": claim.get("fault") or "unknown",
                "PolicyType": claim.get("claim_type") or "unknown",
                "VehicleCategory": claim.get("vehicle_category") or "unknown",
                "VehiclePrice": claim.get("vehicle_price_band") or "unknown",
                "PastNumberOfClaims": claim.get("past_number_of_claims") or "none",
                "AgeOfVehicle": claim.get("age_of_vehicle") or "unknown",
                "AgeOfPolicyHolder": "unknown",
                "PoliceReportFiled": claim.get("police_report_filed") or "No",
                "WitnessPresent": claim.get("witness_present") or "No",
                "AgentType": "External",
                "NumberOfSuppliments": "none",
                "AddressChange_Claim": claim.get("address_change_claim") or "no change",
                "NumberOfCars": "1 vehicle",
                "BasePolicy": claim.get("base_policy") or claim.get("claim_type") or "unknown",
                "Days_Policy_Accident": "more than 30",
                "Days_Policy_Claim": claim.get("days_policy_claim") or "more than 30",
            }
        ]
    )


def score_ml(claim: Mapping[str, Any]) -> dict[str, Any]:
    artifact = load_fraud_artifact()
    preprocessor = artifact["preprocessor"]
    model = artifact["model"]
    threshold = float(artifact.get("threshold", 0.5))
    feature_columns = artifact["feature_columns"]

    row = _claim_to_ml_row(claim)
    # Align to training columns
    for col in feature_columns:
        if col not in row.columns:
            row[col] = "unknown" if col[0].isupper() and col not in {"Age", "Deductible", "DriverRating"} else 0
    encoded = preprocessor.transform(row[feature_columns])
    proba = float(model.predict_proba(encoded)[0][1])
    return {
        "ml_probability": proba,
        "ml_flag": proba >= threshold,
        "threshold": threshold,
    }


def compute_composite_score(
    claim: Any,
    amount_p90_by_type: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """
    Combine rules + ML + anomaly into fraud_score 0–100.

    Returns component scores and human-readable rule hits.
    """
    mapping = claim_model_to_mapping(claim) if not isinstance(claim, Mapping) else dict(claim)

    rules: RuleResult = evaluate_rules(mapping, amount_p90_by_type)
    ml = score_ml(mapping)
    anomaly = score_anomaly(mapping)

    rules_norm = rules.score / 100.0
    ml_prob = ml["ml_probability"]
    if anomaly["is_anomaly"]:
        anomaly_norm = 1.0
    else:
        anomaly_norm = (anomaly["anomaly_score"] / 100.0) * 0.5

    composite = 100.0 * (
        WEIGHT_RULES * rules_norm + WEIGHT_ML * ml_prob + WEIGHT_ANOMALY * anomaly_norm
    )
    composite = float(max(0.0, min(100.0, round(composite, 2))))

    return {
        "fraud_score": composite,
        "components": {
            "rules_score": round(rules.score, 2),
            "rules_weighted": round(WEIGHT_RULES * rules_norm * 100.0, 2),
            "ml_probability": round(ml_prob, 4),
            "ml_weighted": round(WEIGHT_ML * ml_prob * 100.0, 2),
            "anomaly_flag": anomaly["is_anomaly"],
            "anomaly_score": round(anomaly["anomaly_score"], 2),
            "anomaly_weighted": round(WEIGHT_ANOMALY * anomaly_norm * 100.0, 2),
        },
        "weights": {
            "rules": WEIGHT_RULES,
            "ml": WEIGHT_ML,
            "anomaly": WEIGHT_ANOMALY,
        },
        "rule_hits": [
            {"rule_id": h.rule_id, "points": h.points, "reason": h.reason} for h in rules.hits
        ],
        "ml_flag": ml["ml_flag"],
        "ml_threshold": ml["threshold"],
    }


COMPOSITE_FORMULA_DOC = (
    "fraud_score = 100 * (0.35 * rules/100 + 0.45 * P(fraud) + 0.20 * anomaly_norm); "
    "anomaly_norm = 1.0 if IsolationForest anomaly else 0.5 * anomaly_intensity/100"
)
