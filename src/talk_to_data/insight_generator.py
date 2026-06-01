"""Translate Talk-to-Data SQL results into plain-English business insights."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

from src.talk_to_data.prompt_templates import build_insight_prompt
from src.utils.config import settings
from src.utils.logger import get_logger
import google.generativeai as genai

logger = get_logger(__name__)

MAX_ROWS_FOR_INSIGHT = 25
MAX_PREVIEW_CHARS = 6000


@dataclass(frozen=True)
class InsightResult:
    """Business narrative generated from query results."""

    question: str
    sql: str
    business_insight: str
    rows_used: int
    rows_total: int


class GeminiInsightGenerator:
    """Summarize validated SQL output for business users."""

    def __init__(self) -> None:
        """Initialize the Gemini insight generator."""
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for business insight generation")
        

        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    @staticmethod
    def _rows_preview(rows: List[Dict[str, object]]) -> tuple[str, int, int]:
        """Serialize a bounded preview of SQL rows for the LLM prompt."""
        total = len(rows)
        preview_rows = rows[:MAX_ROWS_FOR_INSIGHT]
        preview = json.dumps(preview_rows, indent=2, default=str)
        if len(preview) > MAX_PREVIEW_CHARS:
            preview = preview[:MAX_PREVIEW_CHARS] + "\n... (truncated)"
        return preview, len(preview_rows), total

    def summarize(self, question: str, sql: str, rows: List[Dict[str, object]]) -> InsightResult:
        """Generate a plain-English business answer from query results."""
        preview, rows_used, rows_total = self._rows_preview(rows)
        prompt = build_insight_prompt(question, sql, preview, rows_total)
        response = self.model.generate_content(prompt)
        insight = str(response.text).strip()
        logger.info("Generated business insight for %s-row result set", rows_total)
        return InsightResult(
            question=question,
            sql=sql,
            business_insight=insight,
            rows_used=rows_used,
            rows_total=rows_total,
        )
