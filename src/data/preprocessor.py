"""Model-ready preprocessing for applicant-level credit risk features."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


TARGET_COLUMN = "TARGET"
ID_COLUMN = "SK_ID_CURR"


@dataclass(frozen=True)
class SplitData:
    """Container for train, validation, and test matrices."""

    x_train: pd.DataFrame
    x_val: pd.DataFrame
    x_test: pd.DataFrame
    y_train: pd.Series
    y_val: pd.Series
    y_test: pd.Series
    train_ids: pd.Series
    val_ids: pd.Series
    test_ids: pd.Series


class CreditRiskPreprocessor:
    """Clean, encode, and scale engineered credit-risk features."""

    def __init__(self, max_feature_cardinality: int = settings.max_feature_cardinality) -> None:
        """Initialize the preprocessor.

        Args:
            max_feature_cardinality: Maximum categorical cardinality allowed for
                one-hot encoded features.
        """
        self.max_feature_cardinality = max_feature_cardinality
        self.pipeline: ColumnTransformer | None = None
        self.feature_columns: List[str] = []
        self.numeric_columns: List[str] = []
        self.categorical_columns: List[str] = []

    def clean(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Apply evidence-preserving cleaning without dropping sparse features."""
        cleaned = frame.copy()
        cleaned = cleaned.drop_duplicates(subset=[ID_COLUMN])
        if "CODE_GENDER" in cleaned.columns:
            cleaned["CODE_GENDER"] = cleaned["CODE_GENDER"].replace("XNA", np.nan)
        if "DAYS_EMPLOYED" in cleaned.columns:
            cleaned["DAYS_EMPLOYED"] = cleaned["DAYS_EMPLOYED"].replace(365243, np.nan)
        amount_columns = [column for column in cleaned.columns if column.startswith("AMT_")]
        for column in amount_columns:
            cleaned.loc[cleaned[column] < 0, column] = np.nan
        logger.info("Cleaned feature frame from %s to %s rows", len(frame), len(cleaned))
        return cleaned

    def _select_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Select model features while preserving business-relevant columns."""
        excluded = {TARGET_COLUMN, ID_COLUMN}
        selected = frame.drop(columns=[column for column in excluded if column in frame.columns])
        categorical_columns = selected.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
        high_cardinality = [
            column
            for column in categorical_columns
            if selected[column].nunique(dropna=True) > self.max_feature_cardinality
        ]
        if high_cardinality:
            logger.warning(
                "Dropping high-cardinality categorical features: %s",
                ", ".join(high_cardinality),
            )
            selected = selected.drop(columns=high_cardinality)
        return selected

    def build_pipeline(self, frame: pd.DataFrame) -> ColumnTransformer:
        """Build the sklearn preprocessing transformer for selected features."""
        self.numeric_columns = frame.select_dtypes(include=[np.number]).columns.tolist()
        self.categorical_columns = [
            column for column in frame.columns if column not in self.numeric_columns
        ]
        numeric_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
            ],
        )
        categorical_pipeline = Pipeline(
            steps=[
                ("imputer", SimpleImputer(strategy="most_frequent")),
                ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
            ],
        )
        transformer = ColumnTransformer(
            transformers=[
                ("numeric", numeric_pipeline, self.numeric_columns),
                ("categorical", categorical_pipeline, self.categorical_columns),
            ],
            remainder="drop",
            verbose_feature_names_out=False,
        )
        return transformer

    def fit_transform(self, frame: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Fit preprocessing on a feature frame and return transformed features."""
        cleaned = self.clean(frame)
        y = cleaned[TARGET_COLUMN].astype(int)
        ids = cleaned[ID_COLUMN]
        x = self._select_features(cleaned)
        self.feature_columns = x.columns.tolist()
        self.pipeline = self.build_pipeline(x)
        transformed = self.pipeline.fit_transform(x)
        columns = self.pipeline.get_feature_names_out()
        transformed_frame = pd.DataFrame(transformed, columns=columns, index=cleaned.index)
        logger.info("Preprocessed feature matrix shape: %s", transformed_frame.shape)
        return transformed_frame, y, ids

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Transform new applicant features using a fitted preprocessor."""
        if self.pipeline is None:
            raise RuntimeError("Preprocessor has not been fitted")
        cleaned = self.clean(frame)
        selected = self._select_features(cleaned)
        selected = selected.reindex(columns=self.feature_columns, fill_value=np.nan)
        transformed = self.pipeline.transform(selected)
        return pd.DataFrame(transformed, columns=self.pipeline.get_feature_names_out())

    def split(self, x: pd.DataFrame, y: pd.Series, ids: pd.Series) -> SplitData:
        """Create stratified train, validation, and test splits."""
        x_train_val, x_test, y_train_val, y_test, ids_train_val, ids_test = train_test_split(
            x,
            y,
            ids,
            test_size=settings.test_size,
            random_state=settings.random_state,
            stratify=y,
        )
        val_ratio = settings.validation_size / (1.0 - settings.test_size)
        x_train, x_val, y_train, y_val, ids_train, ids_val = train_test_split(
            x_train_val,
            y_train_val,
            ids_train_val,
            test_size=val_ratio,
            random_state=settings.random_state,
            stratify=y_train_val,
        )
        return SplitData(x_train, x_val, x_test, y_train, y_val, y_test, ids_train, ids_val, ids_test)

    def save(self, path: Path = settings.preprocessor_path) -> None:
        """Persist the fitted preprocessor artifact."""
        if self.pipeline is None:
            raise RuntimeError("Cannot save an unfitted preprocessor")
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "feature_columns": self.feature_columns,
                "numeric_columns": self.numeric_columns,
                "categorical_columns": self.categorical_columns,
            },
            path,
        )
        logger.info("Saved preprocessor to %s", path)

    @classmethod
    def load(cls, path: Path = settings.preprocessor_path) -> "CreditRiskPreprocessor":
        """Load a persisted preprocessor artifact."""
        artifact: Dict[str, object] = joblib.load(path)
        instance = cls()
        instance.pipeline = artifact["pipeline"]  # type: ignore[assignment]
        instance.feature_columns = list(artifact["feature_columns"])  # type: ignore[arg-type]
        instance.numeric_columns = list(artifact["numeric_columns"])  # type: ignore[arg-type]
        instance.categorical_columns = list(artifact["categorical_columns"])  # type: ignore[arg-type]
        return instance


def prepare_model_data(feature_store_path: Path = settings.feature_store_path) -> SplitData:
    """Load the feature store, preprocess it, and save processed splits."""
    frame = pd.read_parquet(feature_store_path)
    preprocessor = CreditRiskPreprocessor()
    x, y, ids = preprocessor.fit_transform(frame)
    split = preprocessor.split(x, y, ids)
    preprocessor.save()
    output_dir = settings.documents_dir / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, value in {
        "x_train": split.x_train,
        "x_val": split.x_val,
        "x_test": split.x_test,
        "y_train": split.y_train.to_frame(TARGET_COLUMN),
        "y_val": split.y_val.to_frame(TARGET_COLUMN),
        "y_test": split.y_test.to_frame(TARGET_COLUMN),
        "train_ids": split.train_ids.to_frame(ID_COLUMN),
        "val_ids": split.val_ids.to_frame(ID_COLUMN),
        "test_ids": split.test_ids.to_frame(ID_COLUMN),
    }.items():
        value.to_parquet(output_dir / f"{name}.parquet", index=False)
    logger.info("Saved processed train/validation/test splits to %s", output_dir)
    return split


def main() -> None:
    """Prepare model-ready data from the configured feature store."""
    prepare_model_data()


if __name__ == "__main__":
    main()
