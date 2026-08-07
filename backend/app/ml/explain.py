"""
SHAP explainability for the XGBoost fraud classifier.

Translates feature attributions into ranked plain-English reasons
suitable for analyst / judge-facing UI.
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any

import numpy as np
import shap

from app.ml.fraud_model import _claim_to_ml_row, load_fraud_artifact

FEATURE_PLAIN_ENGLISH: dict[str, str] = {
    "Age": "Claimant age",
    "Deductible": "Policy deductible",
    "DriverRating": "Driver rating",
    "Sex": "Claimant sex",
    "MaritalStatus": "Marital status",
    "Make": "Vehicle make",
    "AccidentArea": "Accident area",
    "Fault": "Fault assignment",
    "PolicyType": "Policy type",
    "VehicleCategory": "Vehicle category",
    "VehiclePrice": "Vehicle price band",
    "PastNumberOfClaims": "Past number of claims",
    "AgeOfVehicle": "Age of vehicle",
    "AgeOfPolicyHolder": "Age of policy holder",
    "PoliceReportFiled": "Police report filed",
    "WitnessPresent": "Witness present",
    "AgentType": "Agent type",
    "NumberOfSuppliments": "Number of supplements",
    "AddressChange_Claim": "Address change vs claim",
    "NumberOfCars": "Number of cars",
    "BasePolicy": "Base policy",
    "Days_Policy_Accident": "Days from policy to accident",
    "Days_Policy_Claim": "Days from policy to claim",
}


def _base_feature_name(encoded_name: str, feature_columns: list[str]) -> str:
    """Map OneHotEncoder feature name back to original column when possible."""
    for col in feature_columns:
        if (
            encoded_name == col
            or encoded_name.startswith(f"cat__{col}_")
            or encoded_name.startswith(f"{col}_")
        ):
            return col
        if encoded_name.startswith("num__") and encoded_name.endswith(col):
            return col
    # sklearn ColumnTransformer get_feature_names_out style: cat__Make_Honda
    if "__" in encoded_name:
        remainder = encoded_name.split("__", 1)[1]
        for col in feature_columns:
            if remainder == col or remainder.startswith(f"{col}_"):
                return col
    return encoded_name


def _reason_text(
    base_feature: str,
    raw_value: Any,
    shap_value: float,
    claim: Mapping[str, Any],
) -> str:
    label = FEATURE_PLAIN_ENGLISH.get(base_feature, base_feature)
    direction = "increased" if shap_value > 0 else "decreased"
    value_str = str(raw_value)

    if base_feature == "VehiclePrice":
        amount = claim.get("claim_amount")
        if amount:
            return (
                f"{label} '{value_str}' with claim amount ${float(amount):,.0f} "
                f"{direction} fraud risk."
            )
    if base_feature == "PastNumberOfClaims":
        return f"Prior claim history ({value_str}) {direction} the fraud probability."
    if base_feature == "PoliceReportFiled" and str(raw_value).lower() == "no":
        return "Absence of a police report increased fraud risk."
    if base_feature == "WitnessPresent" and str(raw_value).lower() == "no":
        return "No witness present contributed to higher fraud risk."
    if base_feature == "AddressChange_Claim":
        return f"Address-change timing ({value_str}) {direction} fraud risk."
    if base_feature == "Days_Policy_Claim":
        return f"Short policy-to-claim interval ({value_str}) {direction} fraud risk."
    if base_feature == "Age" and shap_value > 0:
        return f"Claimant age ({value_str}) was associated with higher fraud risk for this profile."
    if base_feature == "Fault":
        return f"Fault assignment ({value_str}) {direction} fraud risk."

    return f"{label} = {value_str} {direction} the model's fraud probability."


@lru_cache
def _get_explainer() -> tuple[Any, Any, list[str]]:
    artifact = load_fraud_artifact()
    model = artifact["model"]
    preprocessor = artifact["preprocessor"]
    explainer = shap.TreeExplainer(model)
    return explainer, preprocessor, artifact["feature_columns"]


def explain_claim(
    claim: Mapping[str, Any] | Any, top_k: int = 5
) -> list[dict[str, Any]]:
    """
    Return a ranked list of plain-English SHAP reasons (not raw arrays).
    """
    if not isinstance(claim, Mapping):
        from app.ml.rule_engine import claim_model_to_mapping

        claim_map = claim_model_to_mapping(claim)
    else:
        claim_map = dict(claim)

    explainer, preprocessor, feature_columns = _get_explainer()
    row = _claim_to_ml_row(claim_map)
    encoded = preprocessor.transform(row[feature_columns])

    shap_values = explainer.shap_values(encoded)
    # Binary classifier: shap_values may be list [class0, class1] or 2D array for class 1
    if isinstance(shap_values, list):
        values = np.asarray(shap_values[1][0])
    else:
        arr = np.asarray(shap_values)
        values = arr[0] if arr.ndim == 2 else arr

    try:
        encoded_names = list(preprocessor.get_feature_names_out())
    except Exception:  # noqa: BLE001
        encoded_names = [f"f{i}" for i in range(len(values))]

    # Aggregate absolute SHAP by base feature
    agg: dict[str, float] = {}
    signed: dict[str, float] = {}
    for name, val in zip(encoded_names, values, strict=False):
        base = _base_feature_name(str(name), feature_columns)
        agg[base] = agg.get(base, 0.0) + abs(float(val))
        signed[base] = signed.get(base, 0.0) + float(val)

    ranked = sorted(agg.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
    reasons: list[dict[str, Any]] = []
    for base, importance in ranked:
        raw_value = row[base].iloc[0] if base in row.columns else "n/a"
        shap_signed = signed.get(base, 0.0)
        reasons.append(
            {
                "feature": base,
                "importance": round(float(importance), 6),
                "shap_value": round(float(shap_signed), 6),
                "reason": _reason_text(base, raw_value, shap_signed, claim_map),
            }
        )
    return reasons
