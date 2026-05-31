"""Model evaluation for credit default prediction."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict

from src.utils.config import settings

os.environ.setdefault("MPLCONFIGDIR", str(settings.documents_dir / ".matplotlib"))

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from src.ml.train import append_anomaly_score
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)


BASE_MODEL_FILES = {
    "logistic_reg": "logistic_reg.pkl",
    "random_forest": "random_forest.pkl",
    "xgboost_model": "xgboost_model.pkl",
}


def _load_test_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load processed test data and append anomaly scores."""
    x_test = pd.read_parquet(settings.documents_dir / "processed" / "x_test.parquet")
    y_test = pd.read_parquet(settings.documents_dir / "processed" / "y_test.parquet")["TARGET"]
    iso_forest = joblib.load(settings.models_dir / "iso_forest.pkl")
    (x_test_scored,) = append_anomaly_score(iso_forest, x_test)
    return x_test_scored, y_test


def predict_probabilities(x_test: pd.DataFrame) -> np.ndarray:
    """Generate stacked default probabilities for the test matrix."""
    metadata = joblib.load(settings.models_dir / "meta_learner.pkl")
    meta_learner = metadata
    base_models = {
        name: joblib.load(settings.models_dir / filename)
        for name, filename in BASE_MODEL_FILES.items()
    }
    meta_features = np.column_stack(
        [base_models[name].predict_proba(x_test)[:, 1] for name in BASE_MODEL_FILES],
    )
    return meta_learner.predict_proba(meta_features)[:, 1]


def evaluate_models(output_dir: Path = settings.documents_dir / "evaluation") -> Dict[str, object]:
    """Evaluate the stacked ensemble and write metrics plus plots."""
    output_dir.mkdir(parents=True, exist_ok=True)
    x_test, y_test = _load_test_data()
    probabilities = predict_probabilities(x_test)
    predictions = (probabilities >= settings.low_risk_threshold).astype(int)

    precision, recall, _ = precision_recall_curve(y_test, probabilities)
    fpr, tpr, _ = roc_curve(y_test, probabilities)
    cm = confusion_matrix(y_test, predictions)
    metrics: Dict[str, object] = {
        "roc_auc": float(roc_auc_score(y_test, probabilities)),
        "pr_auc": float(average_precision_score(y_test, probabilities)),
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1": float(f1_score(y_test, predictions, zero_division=0)),
        "confusion_matrix": cm.tolist(),
    }

    plt.figure(figsize=(7, 5))
    plt.plot(fpr, tpr)
    plt.xlabel("False Positive Rate")
    plt.ylabel("True Positive Rate")
    plt.title("ROC Curve")
    plt.savefig(output_dir / "roc_curve.png", dpi=140, bbox_inches="tight")
    plt.close()

    plt.figure(figsize=(7, 5))
    plt.plot(recall, precision)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title("Precision-Recall Curve")
    plt.savefig(output_dir / "pr_curve.png", dpi=140, bbox_inches="tight")
    plt.close()

    ConfusionMatrixDisplay(cm).plot()
    plt.savefig(output_dir / "confusion_matrix.png", dpi=140, bbox_inches="tight")
    plt.close()

    write_json(metrics, output_dir / "evaluation_report.json")
    markdown = [
        "# Evaluation Report",
        "",
        f"- ROC-AUC: {metrics['roc_auc']:.4f}",
        f"- PR-AUC: {metrics['pr_auc']:.4f}",
        f"- Precision: {metrics['precision']:.4f}",
        f"- Recall: {metrics['recall']:.4f}",
        f"- F1: {metrics['f1']:.4f}",
        f"- Classification threshold: {settings.low_risk_threshold:.2f} (MEDIUM or HIGH risk)",
        f"- High-risk threshold: {settings.high_risk_threshold:.2f}",
        "",
        "## Risk Band Policy",
        f"- LOW: probability < {settings.low_risk_threshold:.2f}",
        f"- MEDIUM: {settings.low_risk_threshold:.2f} <= probability <= {settings.high_risk_threshold:.2f}",
        f"- HIGH: probability > {settings.high_risk_threshold:.2f}",
    ]
    (output_dir / "evaluation_report.md").write_text("\n".join(markdown), encoding="utf-8")
    logger.info("Wrote evaluation outputs to %s", output_dir)
    return metrics


def main() -> None:
    """Run model evaluation."""
    evaluate_models()


if __name__ == "__main__":
    main()
