"""Deterministic Talk-to-Data fallback when Gemini is unavailable."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from src.talk_to_data.prompt_templates import FEW_SHOT_EXAMPLES
from src.talk_to_data.sql_validator import SQLValidator
from src.talk_to_data.verified_queries import VERIFIED_QUERIES
from src.utils.logger import get_logger


logger = get_logger(__name__)


def _parse_few_shot_sql() -> Dict[str, str]:
    """Parse question→SQL pairs embedded in few-shot prompt text."""
    mapping: Dict[str, str] = {}
    blocks = re.split(r"\n\s*\n", FEW_SHOT_EXAMPLES.strip())
    for block in blocks:
        lines = [line.strip() for line in block.strip().splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        if not lines[0].lower().startswith("question:"):
            continue
        question = lines[0].split(":", 1)[1].strip().lower()
        sql_lines = []
        for line in lines[1:]:
            if line.lower().startswith("sql:"):
                sql_lines.append(line.split(":", 1)[1].strip())
            else:
                sql_lines.append(line)
        mapping[question] = " ".join(sql_lines).replace("  ", " ").strip()
    return mapping


VERIFIED_SQL_MAP: Dict[str, str] = _parse_few_shot_sql()


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def match_verified_sql(question: str) -> Optional[str]:
    """Return SQL for a verified question using exact or fuzzy word overlap match."""
    normalized = _normalize_question(question)
    if normalized in VERIFIED_SQL_MAP:
        return VERIFIED_SQL_MAP[normalized]
    
    # Try exact substring matching first
    for verified in VERIFIED_QUERIES:
        key = _normalize_question(verified.question)
        if key == normalized or key in normalized or normalized in key:
            return VERIFIED_SQL_MAP.get(key)
            
    # Try word set overlap (Jaccard similarity) to match variations in phrasing
    def get_words(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower()))
        
    q_words = get_words(normalized)
    if not q_words:
        return None
        
    best_match = None
    best_score = 0.0
    
    for verified in VERIFIED_QUERIES:
        key = _normalize_question(verified.question)
        k_words = get_words(key)
        intersection = q_words.intersection(k_words)
        union = q_words.union(k_words)
        score = len(intersection) / len(union) if union else 0.0
        
        # Require at least 40% word overlap to prevent false positive matches
        if score > best_score and score >= 0.4:
            best_score = score
            best_match = key
            
    if best_match:
        logger.info("Fuzzy matched '%s' to '%s' with Jaccard score %.2f", question, best_match, best_score)
        return VERIFIED_SQL_MAP.get(best_match)
        
    return None


def generate_sql_fallback(question: str) -> Tuple[str, bool, List[str]]:
    """Return SQL from the verified catalog when Gemini is not configured."""
    sql = match_verified_sql(question)
    if not sql:
        return (
            "",
            False,
            [
                "No Gemini API key and no verified-query match. "
                "Set GEMINI_API_KEY or use one of the documented verified questions.",
            ],
        )
    validation = SQLValidator().validate(sql)
    logger.info("Using fallback SQL for verified question match")
    return sql, validation.is_valid, validation.errors


def summarize_rows_fallback(question: str, sql: str, rows: List[Dict[str, object]]) -> str:
    """Build a plain-English summary without an LLM."""
    if not rows:
        return (
            f"The query ran successfully but returned no rows for: {question}. "
            "Try broadening the filters or confirm the database has been built."
        )
    if len(rows) == 1 and len(rows[0]) == 1:
        key, value = next(iter(rows[0].items()))
        return (
            f"Answer: {key} = {value} for the question \"{question}\". "
            f"This result was computed with fallback mode (no Gemini API call)."
        )
    preview = json.dumps(rows[:5], indent=2, default=str)
    if len(rows) > 5:
        preview += f"\n... and {len(rows) - 5} more rows."
    return (
        f"Found {len(rows)} rows for \"{question}\".\n"
        f"Key results (first rows):\n{preview}\n"
        "Summary generated in offline fallback mode without Gemini."
    )
