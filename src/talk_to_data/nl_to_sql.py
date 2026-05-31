"""Natural-language to SQL generation using Gemini 2.5 Flash."""

from __future__ import annotations

from dataclasses import dataclass

from src.talk_to_data.prompt_templates import build_sql_prompt
from src.talk_to_data.sql_validator import SQLValidator
from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


@dataclass(frozen=True)
class SQLGenerationResult:
    """Generated SQL and validation details."""

    question: str
    sql: str
    is_valid: bool
    validation_errors: list[str]


class GeminiNLToSQL:
    """Generate SQLite SELECT queries from natural-language questions."""

    def __init__(self, validator: SQLValidator | None = None) -> None:
        """Initialize the Gemini NL-to-SQL engine."""
        self.validator = validator or SQLValidator()
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is required for NL-to-SQL generation")
        import google.generativeai as genai

        genai.configure(api_key=settings.gemini_api_key)
        self.model = genai.GenerativeModel(settings.gemini_model)

    def generate_sql(self, question: str) -> SQLGenerationResult:
        """Generate and validate SQL for a business question."""
        prompt = build_sql_prompt(question)
        response = self.model.generate_content(prompt)
        sql = str(response.text).strip().strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        validation = self.validator.validate(sql)
        logger.info("Generated SQL for question; valid=%s", validation.is_valid)
        return SQLGenerationResult(
            question=question,
            sql=sql,
            is_valid=validation.is_valid,
            validation_errors=validation.errors,
        )
