"""Centralized logging utilities for the platform."""

from __future__ import annotations

import logging
import sys
from functools import lru_cache

from src.utils.config import settings


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with a consistent format.

    Args:
        name: Logger name, typically `__name__`.

    Returns:
        A standard Python logger configured for console output.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(settings.log_level.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        ),
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger
