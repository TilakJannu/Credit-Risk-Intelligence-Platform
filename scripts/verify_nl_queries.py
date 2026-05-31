"""Run verified Talk-to-Data queries and print a pass/fail report."""

from __future__ import annotations

import sys

from src.database.db_manager import DatabaseManager
from src.talk_to_data.insight_generator import GeminiInsightGenerator
from src.talk_to_data.nl_to_sql import GeminiNLToSQL
from src.talk_to_data.query_runner import QueryRunner
from src.talk_to_data.verified_queries import VERIFIED_QUERIES
from src.utils.config import settings


def main() -> int:
    """Execute all verified queries and print results."""
    if not settings.gemini_api_key:
        print("ERROR: GEMINI_API_KEY is required for live verification.")
        return 1

    DatabaseManager().initialize()
    sql_engine = GeminiNLToSQL()
    runner = QueryRunner()
    insight_engine = GeminiInsightGenerator()
    failures = 0

    for index, case in enumerate(VERIFIED_QUERIES, start=1):
        print(f"\n[{index}/{len(VERIFIED_QUERIES)}] {case.question}")
        generated = sql_engine.generate_sql(case.question)
        if not generated.is_valid:
            failures += 1
            print("  FAIL: invalid SQL")
            for error in generated.validation_errors:
                print(f"    - {error}")
            continue

        rows = runner.run(generated.sql)
        if len(rows) < case.min_rows:
            failures += 1
            print(f"  FAIL: expected >= {case.min_rows} rows, got {len(rows)}")
            continue

        insight = insight_engine.summarize(case.question, generated.sql, rows)
        print("  PASS")
        print(f"  SQL: {generated.sql}")
        print(f"  Rows: {len(rows)}")
        print(f"  Insight: {insight.business_insight[:240]}...")

    print(f"\nCompleted with {failures} failure(s) out of {len(VERIFIED_QUERIES)} queries.")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
