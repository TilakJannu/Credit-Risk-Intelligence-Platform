"""Data loading and validation for Home Credit source datasets.

This module discovers available CSV files, validates required Home Credit
datasets, records dataset statistics, and writes a JSON validation report.
It does not perform preprocessing or feature engineering.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional

import pandas as pd

from src.utils.config import settings
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)


REQUIRED_FILES: Mapping[str, List[str]] = {
    "application_train.csv": ["SK_ID_CURR", "TARGET"],
    "bureau.csv": ["SK_ID_CURR", "SK_ID_BUREAU"],
    "previous_application.csv": ["SK_ID_CURR", "SK_ID_PREV"],
    "installments_payments.csv": ["SK_ID_CURR", "SK_ID_PREV"],
    "credit_card_balance.csv": ["SK_ID_CURR", "SK_ID_PREV"],
    "POS_CASH_balance.csv": ["SK_ID_CURR", "SK_ID_PREV"],
}

OPTIONAL_FILES: Mapping[str, List[str]] = {
    "application_test.csv": ["SK_ID_CURR"],
    "bureau_balance.csv": ["SK_ID_BUREAU"],
    "HomeCredit_columns_description.csv": ["Table", "Row", "Description"],
    "sample_submission.csv": ["SK_ID_CURR", "TARGET"],
}

ENCODINGS = ("utf-8", "latin1")


@dataclass(frozen=True)
class DatasetValidation:
    """Validation summary for a single dataset."""

    name: str
    path: str
    encoding: str
    row_count: int
    column_count: int
    columns: List[str]
    required_columns_present: bool
    missing_required_columns: List[str]
    duplicate_rows: int
    missing_id_counts: Dict[str, int]
    missing_value_columns: Dict[str, float]


class DataLoader:
    """Load and validate Home Credit datasets."""

    def __init__(self, data_dir: Path = settings.data_dir) -> None:
        """Initialize the loader.

        Args:
            data_dir: Directory containing Home Credit CSV files.
        """
        self.data_dir = data_dir

    def discover_csv_files(self) -> Dict[str, Path]:
        """Return all CSV files available in the configured data directory."""
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Data directory does not exist: {self.data_dir}")
        files = {path.name: path for path in sorted(self.data_dir.glob("*.csv"))}
        logger.info("Discovered %s CSV files in %s", len(files), self.data_dir)
        return files

    def validate_required_files(self, discovered: Mapping[str, Path]) -> None:
        """Raise an error when required Home Credit files are missing."""
        missing = sorted(set(REQUIRED_FILES) - set(discovered))
        if missing:
            raise FileNotFoundError(
                "Missing required Home Credit files: " + ", ".join(missing),
            )
        logger.info("All required Home Credit CSV files are present")

    def read_csv(
        self,
        path: Path,
        usecols: Optional[Iterable[str]] = None,
        nrows: Optional[int] = None,
    ) -> pd.DataFrame:
        """Read a CSV file with encoding fallback.

        Args:
            path: CSV path.
            usecols: Optional columns to load.
            nrows: Optional row limit for development workflows.

        Returns:
            Loaded pandas DataFrame.
        """
        last_error: Optional[Exception] = None
        for encoding in ENCODINGS:
            try:
                return pd.read_csv(path, encoding=encoding, usecols=usecols, nrows=nrows)
            except UnicodeDecodeError as exc:
                last_error = exc
        raise UnicodeDecodeError(
            "unknown",
            b"",
            0,
            1,
            f"Unable to read {path} with configured encodings: {last_error}",
        )

    def load_all(self, nrows: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """Load all discovered CSV files after validating required files."""
        discovered = self.discover_csv_files()
        self.validate_required_files(discovered)
        datasets = {
            name: self.read_csv(path, nrows=nrows)
            for name, path in discovered.items()
        }
        logger.info("Loaded %s datasets", len(datasets))
        return datasets

    def load_training_sources(self, nrows: Optional[int] = None) -> Dict[str, pd.DataFrame]:
        """Load required modeling datasets plus useful optional sources."""
        discovered = self.discover_csv_files()
        self.validate_required_files(discovered)
        selected = {
            **{name: discovered[name] for name in REQUIRED_FILES},
            **{
                name: discovered[name]
                for name in OPTIONAL_FILES
                if name in discovered
            },
        }
        datasets = {
            name: self.read_csv(path, nrows=nrows)
            for name, path in selected.items()
        }
        logger.info("Loaded %s training source datasets", len(datasets))
        return datasets

    def validate_dataset(
        self,
        name: str,
        path: Path,
        required_columns: Iterable[str],
    ) -> DatasetValidation:
        """Validate a single dataset and return a structured summary."""
        header = self._read_header(path)
        frame = self.read_csv(path)
        required = list(required_columns)
        missing_columns = [column for column in required if column not in frame.columns]
        id_columns = [column for column in required if column.startswith("SK_ID")]
        missing_id_counts = {
            column: int(frame[column].isna().sum())
            for column in id_columns
            if column in frame.columns
        }
        missing_rates = (
            frame.isna()
            .mean()
            .loc[lambda values: values > 0]
            .sort_values(ascending=False)
            .head(50)
            .round(6)
            .to_dict()
        )
        validation = DatasetValidation(
            name=name,
            path=str(path),
            encoding=header["encoding"],
            row_count=int(len(frame)),
            column_count=int(len(frame.columns)),
            columns=list(frame.columns),
            required_columns_present=not missing_columns,
            missing_required_columns=missing_columns,
            duplicate_rows=int(frame.duplicated().sum()),
            missing_id_counts=missing_id_counts,
            missing_value_columns={key: float(value) for key, value in missing_rates.items()},
        )
        logger.info(
            "Validated %s: %s rows, %s columns",
            name,
            validation.row_count,
            validation.column_count,
        )
        return validation

    def generate_validation_report(self) -> Dict[str, object]:
        """Validate all discovered datasets and write the report to disk."""
        discovered = self.discover_csv_files()
        self.validate_required_files(discovered)
        schemas = {**REQUIRED_FILES, **OPTIONAL_FILES}
        validations = [
            self.validate_dataset(name, path, schemas.get(name, []))
            for name, path in discovered.items()
        ]
        report = {
            "data_directory": str(self.data_dir),
            "required_files": sorted(REQUIRED_FILES),
            "optional_files": sorted(OPTIONAL_FILES),
            "discovered_files": sorted(discovered),
            "missing_required_files": sorted(set(REQUIRED_FILES) - set(discovered)),
            "datasets": [validation.__dict__ for validation in validations],
        }
        write_json(report, settings.validation_report_path)
        logger.info("Wrote validation report to %s", settings.validation_report_path)
        return report

    def _read_header(self, path: Path) -> Dict[str, object]:
        """Read only a CSV header and return the encoding that succeeded."""
        for encoding in ENCODINGS:
            try:
                columns = pd.read_csv(path, encoding=encoding, nrows=0).columns.tolist()
                return {"encoding": encoding, "columns": columns}
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Unable to read CSV header: {path}")


def main() -> None:
    """Run dataset validation as a command-line entry point."""
    loader = DataLoader()
    loader.generate_validation_report()


if __name__ == "__main__":
    main()
