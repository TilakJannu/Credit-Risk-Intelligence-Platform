"""Read-only SQL execution for validated Talk-to-Data queries."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd

from src.database.db_manager import DatabaseManager
from src.talk_to_data.sql_validator import SQLValidator
from src.utils.logger import get_logger


logger = get_logger(__name__)


class QueryRunner:
    """Execute validated read-only SQL queries."""

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        """Initialize the query runner."""
        self.db_manager = db_manager or DatabaseManager()
        self.validator = SQLValidator(self.db_manager)

    def run(self, sql: str) -> List[Dict[str, object]]:
        """Validate and execute a SELECT query."""
        validation = self.validator.validate(sql)
        if not validation.is_valid:
            raise ValueError("; ".join(validation.errors))
        with self.db_manager.connect(read_only=True) as connection:
            frame = pd.read_sql_query(sql, connection)
        logger.info("Executed read-only query returning %s rows", len(frame))
        return frame.to_dict(orient="records")
