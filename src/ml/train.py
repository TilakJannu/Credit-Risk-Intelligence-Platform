"""Model training for the Credit Risk Intelligence Platform."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, clone
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold

from src.data.preprocessor import TARGET_COLUMN, prepare_model_data
from src.utils.config import settings
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)


def _load_processed_split(name: str) -> pd.DataFrame:
    """Load a processed split parquet file."""
    return pd.read_parquet(settings.documents_dir / "processed" / f"{name}.parquet")


def load_processed_data() -> Dict[str, pd.DataFrame | pd.Series]:
    """Load processed train, validation, and test datasets."""
    processed_dir = settings.documents_dir / "processed"
    if not processed_dir.exists():
        logger.info("Processed data not found; generating it from the feature store")
        prepare_model_data()
    data: Dict[str, pd.DataFrame | pd.Series] = {
        "x_train": _load_processed_split("x_train"),
        "x_val": _load_processed_split("x_val"),
        "x_test": _load_processed_split("x_test"),
        "y_train": _load_processed_split("y_train")[TARGET_COLUMN],
        "y_val": _load_processed_split("y_val")[TARGET_COLUMN],
        "y_test": _load_processed_split("y_test")[TARGET_COLUMN],
    }
    return data


def train_isolation_forest(x_train: pd.DataFrame) -> IsolationForest:
    """Train and save the Isolation Forest anomaly detector."""
    model = IsolationForest(
        contamination=settings.isolation_forest_contamination,
        random_state=settings.random_state,
        n_jobs=-1,
    )
    model.fit(x_train)
    settings.models_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, settings.models_dir / "iso_forest.pkl")
    logger.info("Saved Isolation Forest model")
    return model


def append_anomaly_score(
    model: IsolationForest,
    *frames: pd.DataFrame,
) -> Tuple[pd.DataFrame, ...]:
    """Append Isolation Forest anomaly scores to one or more feature matrices."""
    scored = []
    for frame in frames:
        enriched = frame.copy()
        enriched["anomaly_score"] = -model.score_samples(frame)
        scored.append(enriched)
    return tuple(scored)


def build_base_models(y_train: pd.Series) -> Dict[str, BaseEstimator]:
    """Create configured base learners."""
    try:
        from xgboost import XGBClassifier
    except ImportError as exc:
        raise RuntimeError("xgboost is required for Phase 7 training") from exc

    negative = int((y_train == 0).sum())
    positive = int((y_train == 1).sum())
    scale_pos_weight = negative / max(positive, 1)
    return {
        "logistic_reg": LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            n_jobs=-1,
            random_state=settings.random_state,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=250,
            class_weight="balanced_subsample",
            min_samples_leaf=20,
            n_jobs=-1,
            random_state=settings.random_state,
        ),
        "xgboost_model": XGBClassifier(
            n_estimators=450,
            max_depth=4,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="binary:logistic",
            eval_metric="aucpr",
            scale_pos_weight=scale_pos_weight,
            tree_method="hist",
            random_state=settings.random_state,
        ),
    }


def train_base_models(
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_val: pd.DataFrame,
    y_val: pd.Series,
) -> Dict[str, BaseEstimator]:
    """Train and save Logistic Regression, Random Forest, and XGBoost."""
    models = build_base_models(y_train)
    metrics: Dict[str, Dict[str, float]] = {}
    for name, model in models.items():
        logger.info("Training %s", name)
        model.fit(x_train, y_train)
        probabilities = model.predict_proba(x_val)[:, 1]
        metrics[name] = {
            "roc_auc": float(roc_auc_score(y_val, probabilities)),
            "pr_auc": float(average_precision_score(y_val, probabilities)),
        }
        joblib.dump(model, settings.models_dir / f"{name}.pkl")
        logger.info("Saved %s", name)
    write_json(metrics, settings.models_dir / "base_model_validation_metrics.json")
    return models


def train_stacking_ensemble(
    models: Dict[str, BaseEstimator],
    x_train: pd.DataFrame,
    y_train: pd.Series,
    x_val: pd.DataFrame,
    y_val: pd.Series,
) -> LogisticRegression:
    """Train a stacking meta learner using out-of-fold predictions."""
    model_names = list(models)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=settings.random_state)
    oof = np.zeros((len(x_train), len(model_names)))
    for model_index, name in enumerate(model_names):
        base_model = models[name]
        for train_index, holdout_index in folds.split(x_train, y_train):
            fold_model = clone(base_model)
            fold_model.fit(x_train.iloc[train_index], y_train.iloc[train_index])
            oof[holdout_index, model_index] = fold_model.predict_proba(
                x_train.iloc[holdout_index],
            )[:, 1]
    meta_learner = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=settings.random_state,
    )
    meta_learner.fit(oof, y_train)

    val_meta_features = np.column_stack(
        [models[name].predict_proba(x_val)[:, 1] for name in model_names],
    )
    val_probabilities = meta_learner.predict_proba(val_meta_features)[:, 1]
    metrics = {
        "roc_auc": float(roc_auc_score(y_val, val_probabilities)),
        "pr_auc": float(average_precision_score(y_val, val_probabilities)),
        "base_model_order": model_names,
    }
    joblib.dump(meta_learner, settings.models_dir / "meta_learner.pkl")
    write_json(metrics, settings.models_dir / "stacking_validation_metrics.json")
    logger.info("Saved stacking meta learner")
    return meta_learner


def train_all() -> Dict[str, object]:
    """Run anomaly detection, base model, and stacking training phases."""
    logger.info("Starting model data preparation...")
    prepare_model_data()

    data = load_processed_data()
    x_train = data["x_train"]  # type: ignore[assignment]
    x_val = data["x_val"]  # type: ignore[assignment]
    y_train = data["y_train"]  # type: ignore[assignment]
    y_val = data["y_val"]  # type: ignore[assignment]

    logger.info("Training Isolation Forest anomaly detector...")
    iso_forest = train_isolation_forest(x_train)
    x_train_scored, x_val_scored = append_anomaly_score(iso_forest, x_train, x_val)
    x_train_scored.to_parquet(settings.documents_dir / "processed" / "x_train_scored.parquet", index=False)
    x_val_scored.to_parquet(settings.documents_dir / "processed" / "x_val_scored.parquet", index=False)

    logger.info("Training base models...")
    models = train_base_models(x_train_scored, y_train, x_val_scored, y_val)
    logger.info("Training stacking ensemble...")
    meta_learner = train_stacking_ensemble(models, x_train_scored, y_train, x_val_scored, y_val)
    metadata = {
        "model_version": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "training_date": datetime.now(timezone.utc).isoformat(),
        "feature_count": int(x_train_scored.shape[1]),
        "feature_list": list(x_train_scored.columns),
        "base_model_order": list(models),
    }
    write_json(metadata, settings.models_dir / "model_metadata.json")

    # Generate SHAP explainer and save global outputs
    logger.info("Generating SHAP artifacts...")
    from src.explainability.shap_engine import ShapExplainer
    shap_explainer = ShapExplainer()
    shap_explainer.save_global_outputs(x_train_scored.head(500))

    # Generate evaluation metrics
    logger.info("Generating evaluation metrics and reports...")
    from src.ml.evaluate import evaluate_models
    evaluate_models()

    logger.info("Model training and artifact generation completed successfully.")
    return {"iso_forest": iso_forest, "models": models, "meta_learner": meta_learner}


def main() -> None:
    """Train all ML artifacts."""
    train_all()


if __name__ == "__main__":
    main()
