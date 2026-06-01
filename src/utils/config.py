"""Configuration management for the Credit Risk Intelligence Platform.

All configurable values are read from environment variables or `.env`.
The module exposes a single immutable settings object used by every layer.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _repo_root() -> Path:
    """Return the repository root based on this module location."""
    return Path(__file__).resolve().parents[2]


def _env_path(name: str, default: str) -> Path:
    """Return an environment-backed path relative to the repository root."""
    value = os.getenv(name, default)
    path = Path(value)
    return path if path.is_absolute() else _repo_root() / path


def _env_float(name: str, default: float) -> float:
    """Return a float environment value with a safe default."""
    value = os.getenv(name)
    return default if value in (None, "") else float(value)


def _env_int(name: str, default: int) -> int:
    """Return an integer environment value with a safe default."""
    value = os.getenv(name)
    return default if value in (None, "") else int(value)


def _env_optional_int(name: str) -> Optional[int]:
    """Return an optional integer environment value."""
    value = os.getenv(name)
    return None if value in (None, "") else int(value)


@dataclass(frozen=True)
class Settings:
    """Application settings shared by every platform module."""

    repo_root: Path
    data_dir: Path
    documents_dir: Path
    models_dir: Path
    database_path: Path
    log_level: str
    random_state: int
    test_size: float
    validation_size: float
    low_risk_threshold: float
    high_risk_threshold: float
    isolation_forest_contamination: float
    max_train_rows: Optional[int]
    max_feature_cardinality: int
    gemini_api_key: str
    gemini_model: str

    @property
    def validation_report_path(self) -> Path:
        """Return the data validation report path."""
        return self.documents_dir / "data_validation_report.json"

    @property
    def feature_store_path(self) -> Path:
        """Return the engineered feature store path."""
        return self.documents_dir / "feature_store.parquet"

    @property
    def preprocessor_path(self) -> Path:
        """Return the saved preprocessing artifact path."""
        return self.models_dir / "preprocessor.pkl"


def load_settings() -> Settings:
    """Load application settings from environment variables."""
    root = _repo_root()
    return Settings(
        repo_root=root,
        data_dir=_env_path("DATA_DIR", "data"),
        documents_dir=_env_path("DOCUMENTS_DIR", "documents"),
        models_dir=_env_path("MODELS_DIR", "models"),
        database_path=_env_path("DATABASE_PATH", "sql/credit_risk.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        random_state=_env_int("RANDOM_STATE", 42),
        test_size=_env_float("TEST_SIZE", 0.20),
        validation_size=_env_float("VALIDATION_SIZE", 0.20),
        low_risk_threshold=_env_float("LOW_RISK_THRESHOLD", 0.30),
        high_risk_threshold=_env_float("HIGH_RISK_THRESHOLD", 0.60),
        isolation_forest_contamination=_env_float(
            "ISOLATION_FOREST_CONTAMINATION",
            0.08,
        ),
        max_train_rows=_env_optional_int("MAX_TRAIN_ROWS"),
        max_feature_cardinality=_env_int("MAX_FEATURE_CARDINALITY", 100),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    )


settings = load_settings()
