"""SHAP explainability for credit risk predictions."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

from src.utils.config import settings

os.environ.setdefault("MPLCONFIGDIR", str(settings.documents_dir / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.ml.predict import CreditRiskPredictor
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)


class ShapExplainer:
    """Generate global and local SHAP explanations for the XGBoost model."""

    def __init__(self) -> None:
        """Load prediction artifacts and build a tree explainer."""
        self.predictor = CreditRiskPredictor()
        self.model = self.predictor.base_models["xgboost_model"]
        self.explainer = shap.TreeExplainer(self.model)

    def explain(self, applicants: pd.DataFrame, top_n: int = 10) -> List[Dict[str, object]]:
        """Generate top positive and negative SHAP contributors per applicant."""
        scored = self.predictor._prepare(applicants)
        shap_values = self.explainer.shap_values(scored)
        explanations: List[Dict[str, object]] = []
        for row_index in range(len(scored)):
            values = np.asarray(shap_values[row_index])
            contributions = pd.DataFrame(
                {
                    "feature": scored.columns,
                    "value": scored.iloc[row_index].values,
                    "shap_value": values,
                },
            )
            positive = contributions.sort_values("shap_value", ascending=False).head(top_n)
            negative = contributions.sort_values("shap_value", ascending=True).head(top_n)
            explanations.append(
                {
                    "customer_id": int(applicants.iloc[row_index]["SK_ID_CURR"])
                    if "SK_ID_CURR" in applicants.columns
                    else None,
                    "top_positive_contributors": positive.to_dict(orient="records"),
                    "top_negative_contributors": negative.to_dict(orient="records"),
                },
            )
        return explanations

    def save_global_outputs(
        self,
        background: pd.DataFrame,
        output_dir: Path = settings.documents_dir / "shap",
    ) -> Dict[str, str]:
        """Generate and save global SHAP summary and feature-importance outputs."""
        output_dir.mkdir(parents=True, exist_ok=True)
        shap_values = self.explainer.shap_values(background)
        shap.summary_plot(shap_values, background, show=False)
        summary_path = output_dir / "shap_summary.png"
        plt.savefig(summary_path, dpi=140, bbox_inches="tight")
        plt.close()

        importance = (
            pd.DataFrame(
                {
                    "feature": background.columns,
                    "mean_abs_shap": np.abs(shap_values).mean(axis=0),
                },
            )
            .sort_values("mean_abs_shap", ascending=False)
            .reset_index(drop=True)
        )
        importance_path = output_dir / "feature_importance.csv"
        importance.to_csv(importance_path, index=False)
        artifact_path = settings.models_dir / "shap_explainer.pkl"
        joblib.dump(self.explainer, artifact_path)
        output = {
            "summary_plot": str(summary_path),
            "feature_importance": str(importance_path),
            "explainer": str(artifact_path),
        }
        write_json(output, output_dir / "shap_outputs.json")
        logger.info("Saved SHAP outputs to %s", output_dir)
        return output
