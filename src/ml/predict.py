"""Reusable prediction pipeline for credit risk scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import joblib
import numpy as np
import pandas as pd

from src.data.preprocessor import CreditRiskPreprocessor, ID_COLUMN
from src.ml.train import append_anomaly_score
from src.utils.config import settings
from src.utils.helpers import risk_band
from src.utils.logger import get_logger


logger = get_logger(__name__)


BASE_MODEL_ORDER = ["logistic_reg", "random_forest", "xgboost_model"]


@dataclass(frozen=True)
class PredictionResult:
    """Prediction response returned by the inference pipeline."""

    customer_id: int | None
    default_probability: float
    risk_score: int
    risk_band: str
    base_model_probabilities: Dict[str, float]


class CreditRiskPredictor:
    """Load saved artifacts and produce stacked credit-risk predictions."""

    def __init__(self) -> None:
        """Load all required model artifacts."""
        self.preprocessor = CreditRiskPreprocessor.load()
        self.iso_forest = joblib.load(settings.models_dir / "iso_forest.pkl")
        self.base_models = {
            name: joblib.load(settings.models_dir / f"{name}.pkl")
            for name in BASE_MODEL_ORDER
        }
        self.meta_learner = joblib.load(settings.models_dir / "meta_learner.pkl")

    def _prepare(self, applicants: pd.DataFrame) -> pd.DataFrame:
        """Preprocess applicants and append anomaly score."""
        processed = self.preprocessor.transform(applicants)
        (scored,) = append_anomaly_score(self.iso_forest, processed)
        return scored

    def predict(self, applicants: pd.DataFrame) -> List[PredictionResult]:
        """Predict default probability and risk band for applicants."""
        scored = self._prepare(applicants)
        base_probabilities = {
            name: model.predict_proba(scored)[:, 1]
            for name, model in self.base_models.items()
        }
        meta_features = np.column_stack([base_probabilities[name] for name in BASE_MODEL_ORDER])
        final_probabilities = self.meta_learner.predict_proba(meta_features)[:, 1]
        ids = applicants[ID_COLUMN].tolist() if ID_COLUMN in applicants.columns else [None] * len(applicants)
        results = []
        for index, probability in enumerate(final_probabilities):
            probability_float = float(probability)
            results.append(
                PredictionResult(
                    customer_id=None if ids[index] is None else int(ids[index]),
                    default_probability=probability_float,
                    risk_score=int(round(probability_float * 1000)),
                    risk_band=risk_band(
                        probability_float,
                        settings.low_risk_threshold,
                        settings.high_risk_threshold,
                    ),
                    base_model_probabilities={
                        name: float(values[index])
                        for name, values in base_probabilities.items()
                    },
                ),
            )
        logger.info("Generated %s credit-risk predictions", len(results))
        return results


def predict_from_records(records: List[Dict[str, object]]) -> List[Dict[str, object]]:
    """Predict from API-friendly dictionary records."""
    frame = pd.DataFrame.from_records(records)
    return [result.__dict__ for result in CreditRiskPredictor().predict(frame)]
