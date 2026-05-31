"""Feature categorization for EDA and documentation deliverables."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd

from src.utils.config import settings
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)

CATEGORY_RULES: List[tuple[str, tuple[str, ...]]] = [
    ("Identifier", ("SK_ID_CURR", "SK_ID_PREV", "SK_ID_BUREAU")),
    ("Target Label", ("TARGET",)),
    (
        "Bureau & External Credit History",
        ("BUREAU_", "BUREAU_BALANCE_", "BUREAU_STATUS_COUNT_"),
    ),
    ("Previous Loan Applications", ("PREVIOUS_", "PREV_")),
    ("Installment Repayment Behavior", ("INSTALLMENT_",)),
    ("Credit Card Utilization", ("CREDIT_CARD_", "CC_")),
    ("POS / Cash Loan Behavior", ("POS_",)),
    ("Engineered Application Ratios", ("APP_",)),
    ("External Credit Scores", ("EXT_SOURCE",)),
    (
        "Demographics & Application Profile",
        (
            "CODE_GENDER",
            "NAME_",
            "FLAG_",
            "DAYS_",
            "CNT_",
            "REGION_",
            "HOUR_",
            "WEEKDAY_",
            "ORGANIZATION_",
            "OCCUPATION",
            "OWN_",
            "LIVING",
            "FLOOR",
            "LAND",
            "BASEMENT",
            "COMMONAREA",
            "NONLIVING",
            "YEARS_BUILD",
            "FONDKAPREMONT",
            "HOUSETYPE",
            "WALLSMATERIAL",
            "EMERGENCY",
        ),
    ),
    ("Financial Amounts", ("AMT_",)),
]


def categorize_column(column: str) -> str:
    """Assign a business category to a single feature column."""
    upper = column.upper()
    for category, prefixes in CATEGORY_RULES:
        if any(upper == prefix or upper.startswith(prefix) for prefix in prefixes):
            return category
    return "Other Engineered Features"


def build_feature_category_report(columns: List[str]) -> Dict[str, object]:
    """Group feature names into business-readable categories."""
    grouped: Dict[str, List[str]] = {}
    for column in sorted(columns):
        if column == "SK_ID_CURR":
            continue
        category = categorize_column(column)
        grouped.setdefault(category, []).append(column)

    summary = [
        {
            "category": category,
            "feature_count": len(features),
            "sample_features": features[:8],
        }
        for category, features in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    ]
    return {
        "total_features": len(columns),
        "categorized_features": sum(len(features) for features in grouped.values()),
        "categories": summary,
        "category_details": grouped,
    }


def load_or_build_feature_categories(
    feature_store_path: Path = settings.feature_store_path,
    output_path: Path | None = None,
) -> Dict[str, object]:
    """Load saved categories or build them from the feature store columns."""
    output_path = output_path or settings.documents_dir / "eda" / "feature_categories.json"
    if output_path.exists():
        import json

        return json.loads(output_path.read_text(encoding="utf-8"))
    if not feature_store_path.exists():
        return {"message": "Feature store not found. Run feature engineering first."}
    frame = pd.read_parquet(feature_store_path, columns=None)
    report = build_feature_category_report(frame.columns.tolist())
    write_json(report, output_path)
    logger.info("Wrote feature categories to %s", output_path)
    return report


def write_feature_categories(
    columns: List[str],
    output_path: Path = settings.documents_dir / "eda" / "feature_categories.json",
) -> Dict[str, object]:
    """Persist feature categorization for the EDA deliverable."""
    report = build_feature_category_report(columns)
    write_json(report, output_path)
    logger.info("Wrote %s feature categories", len(report.get("categories", [])))
    return report
