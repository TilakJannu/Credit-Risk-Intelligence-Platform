"""Build the SQLite analytics database from platform artifacts."""

from __future__ import annotations

import json
from typing import Dict, List

import pandas as pd

from src.data.loader import DataLoader
from src.database.db_manager import DatabaseManager
from src.ml.evaluate import predict_probabilities
from src.ml.train import append_anomaly_score
from src.utils.config import settings
from src.utils.helpers import risk_band
from src.utils.logger import get_logger


logger = get_logger(__name__)


def build_database() -> None:
    """Initialize SQLite and load available customer and rule artifacts."""
    manager = DatabaseManager()
    manager.initialize()
    application = DataLoader().read_csv(settings.data_dir / "application_train.csv")
    manager.upsert_customers_from_application(application)
    prediction_rows = _load_prediction_rows()
    if prediction_rows:
        manager.replace_predictions(prediction_rows)
    rules_path = settings.documents_dir / "rules" / "business_rules.json"
    if rules_path.exists():
        rules = json.loads(rules_path.read_text(encoding="utf-8")).get("rules", [])
        manager.insert_rules(rules)
    logger.info("Database build completed")


def _load_prediction_rows() -> List[Dict[str, object]]:
    """Load scored model predictions from processed artifacts when available."""
    processed_dir = settings.documents_dir / "processed"
    required = [
        processed_dir / "x_train_scored.parquet",
        processed_dir / "x_val_scored.parquet",
        processed_dir / "x_test.parquet",
        processed_dir / "train_ids.parquet",
        processed_dir / "val_ids.parquet",
        processed_dir / "test_ids.parquet",
        settings.models_dir / "iso_forest.pkl",
        settings.models_dir / "meta_learner.pkl",
    ]
    if not all(path.exists() for path in required):
        logger.warning("Prediction artifacts are incomplete; skipping prediction table population")
        return []

    x_train = pd.read_parquet(processed_dir / "x_train_scored.parquet")
    x_val = pd.read_parquet(processed_dir / "x_val_scored.parquet")
    x_test = pd.read_parquet(processed_dir / "x_test.parquet")
    import joblib

    iso_forest = joblib.load(settings.models_dir / "iso_forest.pkl")
    (x_test_scored,) = append_anomaly_score(iso_forest, x_test)
    frames = [
        (x_train, pd.read_parquet(processed_dir / "train_ids.parquet")["SK_ID_CURR"]),
        (x_val, pd.read_parquet(processed_dir / "val_ids.parquet")["SK_ID_CURR"]),
        (x_test_scored, pd.read_parquet(processed_dir / "test_ids.parquet")["SK_ID_CURR"]),
    ]
    rows: List[Dict[str, object]] = []
    for features, ids in frames:
        probabilities = predict_probabilities(features)
        rows.extend(
            {
                "customer_id": int(customer_id),
                "default_probability": float(probability),
                "risk_score": int(round(float(probability) * 1000)),
                "risk_band": risk_band(
                    float(probability),
                    settings.low_risk_threshold,
                    settings.high_risk_threshold,
                ),
            }
            for customer_id, probability in zip(ids, probabilities)
        )
    logger.info("Prepared %s prediction rows for SQLite", len(rows))
    return rows


def main() -> None:
    """Run database build."""
    build_database()


if __name__ == "__main__":
    main()
