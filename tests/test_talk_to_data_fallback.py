"""Tests for offline Talk-to-Data fallback."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from src.database.db_manager import DatabaseManager
from src.talk_to_data.fallback import generate_sql_fallback, match_verified_sql, summarize_rows_fallback
from src.talk_to_data.service import TalkToDataService


class TalkToDataFallbackTests(unittest.TestCase):
    """Offline chat path without Gemini."""

    @classmethod
    def setUpClass(cls) -> None:
        DatabaseManager().initialize()

    def test_match_verified_sql(self) -> None:
        sql = match_verified_sql("How many customers are in each risk band?")
        self.assertIsNotNone(sql)
        self.assertIn("risk_band", sql.lower())

    def test_generate_sql_fallback_valid(self) -> None:
        sql, is_valid, errors = generate_sql_fallback("What is the overall portfolio default rate?")
        self.assertTrue(is_valid, errors)
        self.assertIn("AVG", sql.upper())

    def test_summarize_rows_fallback(self) -> None:
        text = summarize_rows_fallback(
            "Test",
            "SELECT 1",
            [{"portfolio_default_rate": 0.0807}],
        )
        self.assertIn("0.0807", text)

    @patch("src.talk_to_data.service.settings")
    def test_service_fallback_mode(self, mock_settings) -> None:
        mock_settings.gemini_api_key = ""
        result = TalkToDataService().ask("Show top 10 high-risk customers.")
        self.assertEqual(result.mode, "fallback")
        self.assertTrue(result.rows)
        self.assertTrue(len(result.business_insight) > 10)


if __name__ == "__main__":
    unittest.main()
