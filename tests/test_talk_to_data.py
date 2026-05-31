"""Regression tests for Talk-to-Data NL-to-SQL and query execution."""

from __future__ import annotations

import os
import unittest

from src.database.db_manager import DatabaseManager
from src.talk_to_data.nl_to_sql import GeminiNLToSQL
from src.talk_to_data.query_runner import QueryRunner
from src.talk_to_data.verified_queries import VERIFIED_QUERIES
from src.utils.config import settings


@unittest.skipUnless(
    os.getenv("RUN_GEMINI_TESTS", "").lower() in {"1", "true", "yes"},
    "Set RUN_GEMINI_TESTS=1 and GEMINI_API_KEY to run live NL-to-SQL tests.",
)
class TalkToDataLiveTests(unittest.TestCase):
    """Live Gemini tests — run with RUN_GEMINI_TESTS=1."""

    @classmethod
    def setUpClass(cls) -> None:
        if not settings.gemini_api_key:
            raise unittest.SkipTest("GEMINI_API_KEY is not configured.")
        DatabaseManager().initialize()

    def test_verified_natural_language_queries(self) -> None:
        """Each verified question should produce valid SQL and executable results."""
        runner = QueryRunner()
        engine = GeminiNLToSQL()
        failures = []
        for case in VERIFIED_QUERIES:
            generated = engine.generate_sql(case.question)
            if not generated.is_valid:
                failures.append(f"{case.question} -> invalid SQL: {generated.validation_errors}")
                continue
            rows = runner.run(generated.sql)
            if len(rows) < case.min_rows:
                failures.append(
                    f"{case.question} -> expected >= {case.min_rows} rows, got {len(rows)}",
                )
        self.assertFalse(failures, "Failures:\n" + "\n".join(failures))


class TalkToDataOfflineTests(unittest.TestCase):
    """Offline checks that do not call Gemini."""

    def test_verified_query_catalog_has_at_least_five_entries(self) -> None:
        self.assertGreaterEqual(len(VERIFIED_QUERIES), 5)

    def test_few_shot_examples_cover_verified_questions(self) -> None:
        from src.talk_to_data.prompt_templates import FEW_SHOT_EXAMPLES

        for case in VERIFIED_QUERIES:
            self.assertIn(
                case.question,
                FEW_SHOT_EXAMPLES,
                f"Missing few-shot example for: {case.question}",
            )


if __name__ == "__main__":
    unittest.main()
