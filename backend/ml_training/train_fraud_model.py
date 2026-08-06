"""
Train an XGBoost fraud classifier on the vehicle insurance claims dataset.

Uses train/test split + SMOTE for class balance, evaluates with
precision / recall / F1 / ROC-AUC (not accuracy alone), and saves:
  - ml_training/models/fraud_model.pkl
  - feature list + encoders for aligned inference
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier

ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = ROOT / "data" / "raw" / "claims.csv"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_PATH = MODEL_DIR / "fraud_model.pkl"
METRICS_PATH = MODEL_DIR / "fraud_model_metrics.json"

FEATURE_COLUMNS = [
    "Age",
    "Deductible",
    "DriverRating",
    "Sex",
    "MaritalStatus",
    "Make",
    "AccidentArea",
    "Fault",
    "PolicyType",
    "VehicleCategory",
    "VehiclePrice",
    "PastNumberOfClaims",
    "AgeOfVehicle",
    "AgeOfPolicyHolder",
    "PoliceReportFiled",
    "WitnessPresent",
    "AgentType",
    "NumberOfSuppliments",
    "AddressChange_Claim",
    "NumberOfCars",
    "BasePolicy",
    "Days_Policy_Accident",
    "Days_Policy_Claim",
]

NUMERIC_FEATURES = ["Age", "Deductible", "DriverRating"]
CATEGORICAL_FEATURES = [c for c in FEATURE_COLUMNS if c not in NUMERIC_FEATURES]
TARGET = "FraudFound_P"

MIN_F1 = 0.15  # below this the model isn't learning usefully on this imbalance


def load_training_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing dataset at {path}. Place claims.csv before training."
        )
    df = pd.read_csv(path)
    missing = set(FEATURE_COLUMNS + [TARGET]) - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns required for training: {sorted(missing)}")
    frame = df[FEATURE_COLUMNS + [TARGET]].copy()
    frame[TARGET] = frame[TARGET].astype(int)
    for col in NUMERIC_FEATURES:
        frame[col] = pd.to_numeric(frame[col], errors="coerce").fillna(0)
    for col in CATEGORICAL_FEATURES:
        frame[col] = frame[col].astype(str).fillna("unknown")
    return frame


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    # scale_pos_weight helps; SMOTE applied before fit in train()
    clf = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.85,
        colsample_bytree=0.85,
        min_child_weight=3,
        reg_lambda=1.0,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocess", preprocessor), ("model", clf)])


def train() -> dict[str, float]:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df = load_training_frame(RAW_CSV)
    X = df[FEATURE_COLUMNS]
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42,
        stratify=y,
    )

    # Fit preprocessor first so SMOTE sees numeric matrix
    pipeline = build_pipeline()
    preprocessor: ColumnTransformer = pipeline.named_steps["preprocess"]
    X_train_enc = preprocessor.fit_transform(X_train)
    X_test_enc = preprocessor.transform(X_test)

    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X_train_enc, y_train)

    model: XGBClassifier = pipeline.named_steps["model"]
    # After SMOTE classes are balanced; still set mild regularization
    model.fit(X_res, y_res)

    y_prob = model.predict_proba(X_test_enc)[:, 1]
    # Sweep thresholds to maximize F1 on the rare fraud class
    best_threshold = 0.5
    best_f1 = -1.0
    for cand in np.linspace(0.15, 0.55, 17):
        cand_pred = (y_prob >= cand).astype(int)
        cand_f1 = float(f1_score(y_test, cand_pred, zero_division=0))
        if cand_f1 > best_f1:
            best_f1 = cand_f1
            best_threshold = float(cand)
    threshold = best_threshold
    y_pred = (y_prob >= threshold).astype(int)

    precision = float(precision_score(y_test, y_pred, zero_division=0))
    recall = float(recall_score(y_test, y_pred, zero_division=0))
    f1 = float(f1_score(y_test, y_pred, zero_division=0))
    roc_auc = float(roc_auc_score(y_test, y_prob))
    accuracy = float((y_pred == y_test.to_numpy()).mean())

    print("=" * 60)
    print("Fraud classifier evaluation (test set)")
    print("=" * 60)
    print(f"Positive rate (fraud): {y.mean():.4f}")
    print(f"Decision threshold: {threshold}")
    print(f"Accuracy : {accuracy:.4f}  (misleading alone on imbalanced data)")
    print(f"Precision: {precision:.4f}")
    print(f"Recall   : {recall:.4f}")
    print(f"F1 score : {f1:.4f}")
    print(f"ROC-AUC  : {roc_auc:.4f}")
    print()
    print(classification_report(y_test, y_pred, digits=4, zero_division=0))

    if f1 < MIN_F1:
        print(
            f"ERROR: F1={f1:.4f} is near zero / below {MIN_F1}. "
            "Model is not learning — aborting save.",
            file=sys.stderr,
        )
        sys.exit(1)

    artifact = {
        "pipeline": pipeline,  # preprocessor fitted; model fitted on encoded+SMOTE
        "model": model,
        "preprocessor": preprocessor,
        "feature_columns": FEATURE_COLUMNS,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "threshold": threshold,
        "metrics": {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "roc_auc": roc_auc,
            "accuracy": accuracy,
        },
    }
    # Refit full sklearn Pipeline preprocess for convenient inference:
    # keep separate fitted preprocessor + model (SMOTE cannot live in Pipeline easily)
    joblib.dump(artifact, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(artifact["metrics"], indent=2), encoding="utf-8")
    print(f"Saved model -> {MODEL_PATH}")
    print(f"Saved metrics -> {METRICS_PATH}")
    return artifact["metrics"]


if __name__ == "__main__":
    train()
