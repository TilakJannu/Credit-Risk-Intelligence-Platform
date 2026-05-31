"""Run Phase 5 platform smoke tests and print a submission readiness report."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.utils.config import settings


def main() -> int:
    """Execute smoke tests with configurable ML and Gemini coverage."""
    print("Credit Risk Intelligence Platform — Phase 5 Smoke Test")
    print("=" * 56)
    print(f"Repo root:     {settings.repo_root}")
    print(f"Database:      {settings.database_path} ({'OK' if settings.database_path.exists() else 'MISSING'})")
    print(f"Feature store: {settings.feature_store_path} ({'OK' if settings.feature_store_path.exists() else 'MISSING'})")
    print(f"GEMINI_API_KEY: {'set' if settings.gemini_api_key else 'not set'}")
    print(f"RUN_ML_SMOKE_TESTS: {os.getenv('RUN_ML_SMOKE_TESTS', '0')}")
    print(f"RUN_GEMINI_TESTS:   {os.getenv('RUN_GEMINI_TESTS', '0')}")
    print("=" * 56)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromName("tests.test_platform_smoke"))
    suite.addTests(loader.loadTestsFromName("tests.test_talk_to_data.TalkToDataOfflineTests"))

    if os.getenv("RUN_GEMINI_TESTS", "").lower() in {"1", "true", "yes"} and settings.gemini_api_key:
        suite.addTests(loader.loadTestsFromName("tests.test_talk_to_data.TalkToDataLiveTests"))

    presentation = settings.documents_dir / "project_presentation.pdf"
    if presentation.exists():
        print(f"\nPresentation PDF: {presentation} (OK)")
    else:
        print("\nNOTE: Run `python scripts/generate_presentation_pdf.py` to create project_presentation.pdf")

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print("\n" + "=" * 56)
    if result.wasSuccessful():
        print("SMOKE TEST PASSED — platform ready for demo / submission.")
        return 0
    print("SMOKE TEST FAILED — fix errors above before submitting.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
