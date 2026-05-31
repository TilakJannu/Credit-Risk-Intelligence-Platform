"""Unified explainability: stacking-aligned SHAP, official waterfall, and LIME."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

from src.utils.config import settings

os.environ.setdefault("MPLCONFIGDIR", str(settings.documents_dir / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")
import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from src.explainability.lime_engine import LimeExplainer
from src.explainability.shap_engine import ShapExplainer
from src.ml.predict import BASE_MODEL_ORDER, CreditRiskPredictor
from src.utils.logger import get_logger


logger = get_logger(__name__)

META_FEATURE_LABELS = {
    "logistic_reg": "Logistic Regression PD",
    "random_forest": "Random Forest PD",
    "xgboost_model": "XGBoost PD",
}


class ExplanationService:
    """Produce explanations aligned with the stacking ensemble final score."""

    def __init__(self) -> None:
        """Load explainers and optional LIME background."""
        self.shap_explainer = ShapExplainer()
        self.predictor = self.shap_explainer.predictor
        self._meta_background = self._load_meta_background()
        self._lime: Optional[LimeExplainer] = None

    def _load_meta_background(self) -> np.ndarray:
        """Load validation-set meta features for the stacking LinearExplainer."""
        path = settings.documents_dir / "processed" / "x_val_scored.parquet"
        if not path.exists():
            return np.array([[0.08, 0.08, 0.08]])
        frame = pd.read_parquet(path).head(500)
        probs = {
            name: self.predictor.base_models[name].predict_proba(frame)[:, 1]
            for name in BASE_MODEL_ORDER
        }
        return np.column_stack([probs[name] for name in BASE_MODEL_ORDER])

    def _lime_explainer(self) -> LimeExplainer:
        if self._lime is None:
            self._lime = LimeExplainer()
        return self._lime

    def _stacking_shap(self, base_probabilities: Dict[str, float]) -> Dict[str, object]:
        """SHAP values for the meta-learner (final score drivers)."""
        meta_learner = self.predictor.meta_learner
        meta_explainer = shap.LinearExplainer(meta_learner, self._meta_background)
        meta_row = np.array([[base_probabilities[name] for name in BASE_MODEL_ORDER]])
        shap_values = meta_explainer.shap_values(meta_row)
        if isinstance(shap_values, list):
            shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]
        values = np.asarray(shap_values).reshape(-1)
        base_value = float(np.asarray(meta_explainer.expected_value).reshape(-1)[0])
        contributors = [
            {
                "feature": META_FEATURE_LABELS[name],
                "value": float(base_probabilities[name]),
                "shap_value": float(values[index]),
            }
            for index, name in enumerate(BASE_MODEL_ORDER)
        ]
        positive = sorted(contributors, key=lambda item: item["shap_value"], reverse=True)
        negative = sorted(contributors, key=lambda item: item["shap_value"])
        return {
            "method": "SHAP LinearExplainer on stacking meta-learner",
            "base_value": base_value,
            "top_positive_contributors": positive,
            "top_negative_contributors": negative,
            "note": "These contributions explain the final stacked default probability.",
        }

    def explain_applicants(
        self,
        applicants: pd.DataFrame,
        top_n: int = 10,
        include_lime: bool = True,
    ) -> List[Dict[str, object]]:
        """Return full explanations for each applicant."""
        predictions = self.predictor.predict(applicants)
        feature_shap = self.shap_explainer.explain(applicants, top_n=top_n)
        results: List[Dict[str, object]] = []

        for index, prediction in enumerate(predictions):
            base_probs = prediction.base_model_probabilities
            item: Dict[str, object] = {
                "customer_id": prediction.customer_id,
                "final_prediction": {
                    "default_probability": prediction.default_probability,
                    "risk_score": prediction.risk_score,
                    "risk_band": prediction.risk_band,
                    "base_model_probabilities": base_probs,
                },
                "stacking_shap": self._stacking_shap(base_probs),
                "feature_shap": {
                    "method": "SHAP TreeExplainer on XGBoost (local feature drivers)",
                    "top_positive_contributors": feature_shap[index]["top_positive_contributors"],
                    "top_negative_contributors": feature_shap[index]["top_negative_contributors"],
                },
            }
            if include_lime:
                try:
                    item["lime"] = self._lime_explainer().explain_row(applicants.iloc[[index]], top_n=top_n)
                except Exception as exc:
                    logger.warning("LIME explanation skipped: %s", exc)
                    item["lime"] = {"error": str(exc)}
            results.append(item)
        return results

    def save_waterfall_plot(
        self,
        applicants: pd.DataFrame,
        customer_id: Optional[int] = None,
        output_dir: Path | None = None,
    ) -> str:
        """Save an official SHAP waterfall plot (PNG) and return its API URL path."""
        output_dir = output_dir or settings.documents_dir / "explainability" / "waterfalls"
        output_dir.mkdir(parents=True, exist_ok=True)
        cid = customer_id or int(applicants.iloc[0]["SK_ID_CURR"])
        output_path = output_dir / f"waterfall_{cid}.png"

        scored = self.predictor._prepare(applicants.head(1))
        tree_explainer = self.shap_explainer.explainer
        shap_values = tree_explainer(scored)
        if hasattr(shap_values, "values"):
            explanation = shap_values[0]
        else:
            row_values = tree_explainer.shap_values(scored)
            if isinstance(row_values, list):
                row_values = row_values[1] if len(row_values) > 1 else row_values[0]
            explanation = shap.Explanation(
                values=np.asarray(row_values)[0],
                base_values=tree_explainer.expected_value,
                data=scored.iloc[0].values,
                feature_names=list(scored.columns),
            )
        plt.figure(figsize=(10, 6))
        shap.plots.waterfall(explanation, show=False, max_display=12)
        plt.tight_layout()
        plt.savefig(output_path, dpi=140, bbox_inches="tight")
        plt.close()
        logger.info("Saved SHAP waterfall to %s", output_path)
        return f"/assets/explainability/waterfall_{cid}.png"
