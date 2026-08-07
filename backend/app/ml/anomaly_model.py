"""Load Isolation Forest artifact and score claim anomaly signal."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = (
    Path(__file__).resolve().parents[2] / "ml_training" / "models" / "anomaly_model.pkl"
)


@lru_cache
def load_anomaly_artifact() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Anomaly model not found at {MODEL_PATH}. "
            "Run ml_training/train_anomaly_model.py first."
        )
    return joblib.load(MODEL_PATH)


def _vehicle_price_mid(band: str | None, midpoints: Mapping[str, float]) -> float:
    if not band:
        return 30000.0
    return float(midpoints.get(str(band), 30000.0))


def claim_to_anomaly_features(
    claim: Mapping[str, Any], artifact: dict[str, Any]
) -> pd.DataFrame:
    midpoints = artifact["vehicle_price_midpoints"]
    age = float(claim.get("age") or 0)
    deductible = float(claim.get("deductible") or 400)
    rating = float(claim.get("driver_rating") or 1)
    price = _vehicle_price_mid(claim.get("vehicle_price_band"), midpoints)
    amount = float(claim.get("claim_amount") or 0)
    if amount <= 0:
        amount = max(500.0, price * (0.18 + rating * 0.03) - deductible * 0.5)
    return pd.DataFrame(
        [
            {
                "age": age,
                "deductible": deductible,
                "driver_rating": rating,
                "vehicle_price_mid": price,
                "claim_amount_proxy": amount,
            }
        ]
    )


def score_anomaly(claim: Mapping[str, Any]) -> dict[str, Any]:
    """
    Returns:
      is_anomaly: bool
      anomaly_score: float 0–100 (higher = more anomalous)
      raw_decision: IsolationForest decision_function (higher = more normal)
    """
    artifact = load_anomaly_artifact()
    model = artifact["model"]
    scaler = artifact["scaler"]
    features = claim_to_anomaly_features(claim, artifact)
    scaled = scaler.transform(features[artifact["feature_columns"]])
    pred = int(model.predict(scaled)[0])
    decision = float(model.decision_function(scaled)[0])
    # Map decision (typically ~[-0.2, 0.3]) to 0–100 anomaly intensity
    anomaly_intensity = float(np.clip((0.15 - decision) / 0.35 * 100.0, 0.0, 100.0))
    return {
        "is_anomaly": pred == -1,
        "anomaly_score": anomaly_intensity,
        "raw_decision": decision,
    }
