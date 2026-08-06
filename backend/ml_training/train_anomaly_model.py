"""
Train Isolation Forest anomaly detector on numeric claim features.

Flags novel / unusual claims as a second independent fraud signal.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "claims.csv"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "anomaly_model.pkl"
METRICS_PATH = MODEL_DIR / "anomaly_model_metrics.json"

# VehiclePrice bands → midpoint for a numeric feature
VEHICLE_PRICE_MIDPOINTS = {
    "less than 20000": 15000.0,
    "20000 to 29000": 24500.0,
    "30000 to 39000": 34500.0,
    "40000 to 59000": 49500.0,
    "60000 to 69000": 64500.0,
    "more than 69000": 85000.0,
}

FEATURE_COLUMNS = [
    "age",
    "deductible",
    "driver_rating",
    "vehicle_price_mid",
    "claim_amount_proxy",
]


def build_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    price = df["VehiclePrice"].astype(str).map(VEHICLE_PRICE_MIDPOINTS).fillna(30000.0)
    age = pd.to_numeric(df["Age"], errors="coerce").fillna(0)
    deductible = pd.to_numeric(df["Deductible"], errors="coerce").fillna(400)
    rating = pd.to_numeric(df["DriverRating"], errors="coerce").fillna(1)
    # Same proxy used in seed for claim amount
    fraction = 0.18 + (rating * 0.03)
    claim_amount_proxy = (price * fraction - deductible * 0.5).clip(lower=500)

    return pd.DataFrame(
        {
            "age": age,
            "deductible": deductible,
            "driver_rating": rating,
            "vehicle_price_mid": price,
            "claim_amount_proxy": claim_amount_proxy,
        }
    )


def train(contamination: float = 0.06) -> dict[str, float]:
    """contamination ~ expected anomaly rate; keep as a small minority."""
    if not RAW_CSV.exists():
        raise FileNotFoundError(f"Missing dataset at {RAW_CSV}")

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(RAW_CSV)
    X = build_feature_matrix(raw)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_scaled)

    preds = model.predict(X_scaled)  # -1 = anomaly, 1 = normal
    anomaly_rate = float((preds == -1).mean())
    scores = model.decision_function(X_scaled)

    print("=" * 60)
    print("Isolation Forest anomaly detection")
    print("=" * 60)
    print(f"Rows scored       : {len(X)}")
    print(f"Contamination set : {contamination:.4f}")
    print(f"Anomaly rate      : {anomaly_rate:.4%} ({int((preds == -1).sum())} claims)")
    print(f"Score mean/std    : {scores.mean():.4f} / {scores.std():.4f}")

    if anomaly_rate <= 0.0 or anomaly_rate >= 0.50:
        raise RuntimeError(
            f"Implausible anomaly rate {anomaly_rate:.2%}. "
            "Expected a minority flag rate (not 0%, not 50%+)."
        )

    artifact = {
        "model": model,
        "scaler": scaler,
        "feature_columns": FEATURE_COLUMNS,
        "contamination": contamination,
        "anomaly_rate": anomaly_rate,
        "vehicle_price_midpoints": VEHICLE_PRICE_MIDPOINTS,
    }
    joblib.dump(artifact, MODEL_PATH)
    metrics = {
        "contamination": contamination,
        "anomaly_rate": anomaly_rate,
        "n_samples": int(len(X)),
        "n_anomalies": int((preds == -1).sum()),
    }
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")
    return metrics


if __name__ == "__main__":
    train()
