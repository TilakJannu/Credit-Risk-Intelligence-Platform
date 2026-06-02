"""Talk-to-Data orchestration with Gemini or offline fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from src.talk_to_data.fallback import generate_sql_fallback, summarize_rows_fallback
from src.talk_to_data.insight_generator import GeminiInsightGenerator
from src.talk_to_data.nl_to_sql import GeminiNLToSQL
from src.talk_to_data.query_runner import QueryRunner
from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class ChatResponse:
    """Full Talk-to-Data response."""

    question: str
    sql: str
    rows: List[Dict[str, object]]
    row_count: int
    business_insight: str
    mode: str
    insight_rows_used: int | None = None
    insight_error: str | None = None


class TalkToDataService:
    """Generate SQL, execute queries, and produce business insights."""

    def __init__(self) -> None:
        self.runner = QueryRunner()
        self._use_gemini = bool(settings.gemini_api_key)

    def ask(self, question: str) -> ChatResponse:
        """Answer a business question end-to-end."""
        if self._use_gemini:
            return self._ask_gemini(question)
        return self._ask_fallback(question)

    def _ask_gemini(self, question: str) -> ChatResponse:
        try:
            generated = GeminiNLToSQL().generate_sql(question)
            if not generated.is_valid:
                raise ValueError("; ".join(generated.validation_errors))
            rows = self.runner.run(generated.sql)
            insight_rows_used = None
            try:
                insight = GeminiInsightGenerator().summarize(question, generated.sql, rows)
                business_insight = insight.business_insight
                insight_rows_used = insight.rows_used
            except Exception as exc:
                logger.warning("Gemini insight failed, using fallback summarizer: %s", exc)
                business_insight = summarize_rows_fallback(question, generated.sql, rows)
            return ChatResponse(
                question=question,
                sql=generated.sql,
                rows=rows,
                row_count=len(rows),
                business_insight=business_insight,
                mode="gemini",
                insight_rows_used=insight_rows_used,
            )
        except Exception as exc:
            logger.warning("Gemini SQL generation failed: %s. Falling back to offline mode.", exc)
            return self._ask_fallback(question)

    def _ask_fallback(self, question: str) -> ChatResponse:
        sql, is_valid, errors = generate_sql_fallback(question)
        if not is_valid:
            raise ValueError("; ".join(errors))
        rows = self.runner.run(sql)
        return ChatResponse(
            question=question,
            sql=sql,
            rows=rows,
            row_count=len(rows),
            business_insight=summarize_rows_fallback(question, sql, rows),
            mode="fallback",
        )
