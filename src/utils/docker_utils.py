"""Docker runtime helper checks."""

from __future__ import annotations

import os
from pathlib import Path


def running_in_container() -> bool:
    """Return True when the process appears to run inside a container."""
    return Path("/.dockerenv").exists() or os.getenv("RUNNING_IN_DOCKER") == "1"
