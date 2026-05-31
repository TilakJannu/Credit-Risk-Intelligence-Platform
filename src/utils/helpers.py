"""Shared helper functions used across platform modules."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def ensure_directories(paths: Iterable[Path]) -> None:
    """Create directories when they do not already exist.

    Args:
        paths: Directory paths to create.
    """
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def write_json(payload: Dict[str, Any], path: Path) -> None:
    """Write a JSON payload to disk with stable formatting.

    Args:
        payload: JSON-serializable dictionary.
        path: Destination path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def normalize_column_name(name: str) -> str:
    """Normalize a source column name for derived analytics outputs."""
    return name.strip().lower().replace(" ", "_")


def risk_band(probability: float, low_threshold: float, high_threshold: float) -> str:
    """Convert a default probability into a business risk band."""
    if probability < low_threshold:
        return "LOW"
    if probability <= high_threshold:
        return "MEDIUM"
    return "HIGH"


def top_records(records: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    """Return a bounded list of dictionaries for API-safe responses."""
    return records[: max(limit, 0)]
