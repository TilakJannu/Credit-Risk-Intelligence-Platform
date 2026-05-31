"""SQLite database creation and persistence helpers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, Iterable, List

import pandas as pd

from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    """Manage the SQLite analytics database."""

    def __init__(self, database_path: Path = settings.database_path) -> None:
        """Initialize the database manager."""
        self.database_path = database_path

    def connect(self, read_only: bool = False) -> sqlite3.Connection:
        """Open a SQLite connection."""
        if read_only:
            uri = f"file:{self.database_path}?mode=ro"
            return sqlite3.connect(uri, uri=True)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self.database_path)

    def initialize(self, schema_path: Path = settings.repo_root / "sql" / "schema.sql") -> None:
        """Create database tables from the schema SQL file."""
        schema = schema_path.read_text(encoding="utf-8")
        with self.connect() as connection:
            connection.executescript(schema)
        logger.info("Initialized SQLite database at %s", self.database_path)

    def upsert_customers_from_application(self, application: pd.DataFrame) -> None:
        """Load customer records from the Home Credit application table."""
        customers = pd.DataFrame(
            {
                "sk_id_curr": application["SK_ID_CURR"],
                "target": application.get("TARGET"),
                "income_total": application.get("AMT_INCOME_TOTAL"),
                "credit_amount": application.get("AMT_CREDIT"),
                "annuity": application.get("AMT_ANNUITY"),
                "gender": application.get("CODE_GENDER"),
                "education_type": application.get("NAME_EDUCATION_TYPE"),
                "family_status": application.get("NAME_FAMILY_STATUS"),
                "occupation_type": application.get("OCCUPATION_TYPE"),
                "housing_type": application.get("NAME_HOUSING_TYPE"),
                "age_years": -application.get("DAYS_BIRTH") / 365.25,
                "employment_years": -application.get("DAYS_EMPLOYED").replace(365243, pd.NA) / 365.25,
            },
        )
        with self.connect() as connection:
            customers.to_sql("_customers_staging", connection, if_exists="replace", index=False)
            columns = ", ".join(customers.columns)
            connection.execute(
                f"INSERT OR REPLACE INTO customers ({columns}) SELECT {columns} FROM _customers_staging",
            )
            connection.execute("DROP TABLE _customers_staging")
        logger.info("Inserted %s customer records", len(customers))

    def insert_predictions(self, predictions: Iterable[Dict[str, object]]) -> None:
        """Insert model prediction records."""
        rows = [
            {
                "sk_id_curr": item.get("customer_id"),
                "default_probability": item["default_probability"],
                "risk_score": item["risk_score"],
                "risk_band": item["risk_band"],
            }
            for item in predictions
        ]
        if not rows:
            return
        with self.connect() as connection:
            pd.DataFrame(rows).to_sql("predictions", connection, if_exists="append", index=False)

    def replace_predictions(self, predictions: Iterable[Dict[str, object]]) -> None:
        """Replace all prediction records with a fresh prediction snapshot."""
        with self.connect() as connection:
            connection.execute("DELETE FROM shap_outputs")
            connection.execute("DELETE FROM predictions")
        self.insert_predictions(predictions)

    def insert_rules(self, rules: List[str]) -> None:
        """Insert business rules into the database."""
        if not rules:
            return
        rows = [{"rule_text": rule, "risk_band": "HIGH"} for rule in rules]
        with self.connect() as connection:
            connection.execute("DELETE FROM rules")
            pd.DataFrame(rows).to_sql("rules", connection, if_exists="append", index=False)
