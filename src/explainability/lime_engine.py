"""LIME local interpretable explanations for credit risk features."""

from __future__ import annotations

from functools import lru_cache
from typing import Dict, List

import numpy as np
import pandas as pd
from lime.lime_tabular import LimeTabularExplainer

from src.ml.predict import CreditRiskPredictor
from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _training_background() -> tuple[np.ndarray, List[str]]:
    """Load a sample of processed training rows for LIME background."""
    path = settings.documents_dir / "processed" / "x_train_scored.parquet"
    if not path.exists():
        raise FileNotFoundError("Processed training data required for LIME. Run preprocessing first.")
    frame = pd.read_parquet(path).head(800)
    return frame.values.astype(float), list(frame.columns)


class LimeExplainer:
    """LIME tabular explanations using the stacking predictor as the black-box model."""

    def __init__(self) -> None:
        """Initialize LIME with training background and prediction function."""
        self.predictor = CreditRiskPredictor()
        self.background, self.feature_names = _training_background()
        self.explainer = LimeTabularExplainer(
            self.background,
            feature_names=self.feature_names,
            class_names=["non_default", "default"],
            mode="classification",
            discretize_continuous=True,
            random_state=settings.random_state,
        )

    def _predict_proba(self, rows: np.ndarray) -> np.ndarray:
        """Predict class probabilities for LIME perturbed rows."""
        frame = pd.DataFrame(rows, columns=self.feature_names)
        probabilities = [
            result.default_probability
            for result in self.predictor.predict(frame)
        ]
        probs = np.array(probabilities, dtype=float)
        return np.column_stack([1.0 - probs, probs])

    def explain_row(self, applicants: pd.DataFrame, top_n: int = 10) -> Dict[str, object]:
        """Explain a single applicant with LIME (positive class = default)."""
        scored = self.predictor._prepare(applicants.head(1))
        row = scored.values.astype(float)[0]
        explanation = self.explainer.explain_instance(
            row,
            self._predict_proba,
            num_features=top_n,
            top_labels=(1,),
        )
        pairs = explanation.as_list(label=1)
        contributors = [
            {"feature": feature, "weight": float(weight)}
            for feature, weight in pairs
        ]
        return {
            "method": "LIME tabular (stacking ensemble as black-box model)",
            "label": "default",
            "contributors": contributors,
        }
