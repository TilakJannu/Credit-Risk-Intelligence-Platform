"""Verified natural-language queries for Talk-to-Data regression checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class VerifiedQuery:
    """A business question expected to produce valid, useful SQL."""

    question: str
    description: str
    min_rows: int = 0


VERIFIED_QUERIES: List[VerifiedQuery] = [
    VerifiedQuery(
        question="Show top 10 high-risk customers.",
        description="Join customers and predictions; filter HIGH risk band.",
        min_rows=1,
    ),
    VerifiedQuery(
        question="Which occupation has the highest default rate?",
        description="Aggregate default rate by occupation from customers.target.",
        min_rows=1,
    ),
    VerifiedQuery(
        question="What is the average income by risk band?",
        description="Join predictions to customers and group by risk_band.",
        min_rows=1,
    ),
    VerifiedQuery(
        question="How many customers are in each risk band?",
        description="Count predictions grouped by risk_band.",
        min_rows=1,
    ),
    VerifiedQuery(
        question="What is the average default probability for high-risk customers?",
        description="Aggregate default_probability where risk_band is HIGH.",
        min_rows=1,
    ),
    VerifiedQuery(
        question="Show the top 5 customers with the highest credit amount.",
        description="Order customers by credit_amount descending.",
        min_rows=1,
    ),
    VerifiedQuery(
        question="What is the overall portfolio default rate?",
        description="Average of customers.target across labeled applicants.",
        min_rows=1,
    ),
]
