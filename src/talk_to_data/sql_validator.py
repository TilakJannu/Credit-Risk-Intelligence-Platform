"""SQL validation for read-only Talk-to-Data queries."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Set

import sqlparse

from src.database.db_manager import DatabaseManager


BLOCKED_KEYWORDS = {
    "DELETE",
    "DROP",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "REPLACE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
}


@dataclass(frozen=True)
class ValidationResult:
    """Result of SQL validation."""

    is_valid: bool
    errors: List[str]


class SQLValidator:
    """Validate generated SQL before execution."""

    def __init__(self, db_manager: DatabaseManager | None = None) -> None:
        """Initialize with a database manager."""
        self.db_manager = db_manager or DatabaseManager()

    def get_schema(self) -> Dict[str, Set[str]]:
        """Return available SQLite tables and columns."""
        schema: Dict[str, Set[str]] = {}
        with self.db_manager.connect(read_only=True) as connection:
            table_rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'",
            ).fetchall()
            for (table_name,) in table_rows:
                columns = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
                schema[table_name] = {row[1] for row in columns}
        return schema

    def validate(self, sql: str) -> ValidationResult:
        """Validate that SQL is a safe single SELECT statement."""
        errors: List[str] = []
        parsed = sqlparse.parse(sql)
        if len(parsed) != 1:
            errors.append("Only a single SQL statement is allowed.")
        normalized = sqlparse.format(sql, keyword_case="upper", strip_comments=True).strip()
        if not normalized.upper().startswith("SELECT"):
            errors.append("Only SELECT statements are allowed.")
        tokens = {token.upper() for token in re.findall(r"\b[A-Za-z_]+\b", normalized)}
        blocked = sorted(tokens.intersection(BLOCKED_KEYWORDS))
        if blocked:
            errors.append("Blocked SQL keywords detected: " + ", ".join(blocked))
        try:
            with self.db_manager.connect(read_only=True) as connection:
                connection.execute(f"EXPLAIN QUERY PLAN {normalized}")
        except sqlite3.Error as exc:
            errors.append(f"SQLite validation failed: {exc}")
        return ValidationResult(is_valid=not errors, errors=errors)
