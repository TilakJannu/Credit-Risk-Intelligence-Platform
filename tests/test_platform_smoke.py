"""End-to-end smoke tests for submission readiness (Phase 5 / Final QA)."""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.main import app
from src.utils.config import settings


REQUIRED_MODELS = (
    "preprocessor.pkl",
    "iso_forest.pkl",
    "logistic_reg.pkl",
    "random_forest.pkl",
    "xgboost_model.pkl",
    "meta_learner.pkl",
)


class ArtifactSmokeTests(unittest.TestCase):
    """Verify training and documentation artifacts exist."""

    def test_required_model_artifacts_exist(self) -> None:
        missing = [name for name in REQUIRED_MODELS if not (settings.models_dir / name).exists()]
        self.assertFalse(missing, f"Missing model artifacts: {missing}")

    def test_evaluation_report_exists(self) -> None:
        path = settings.documents_dir / "evaluation" / "evaluation_report.json"
        self.assertTrue(path.exists(), "Run `python -m src.ml.evaluate`")

    def test_eda_report_exists(self) -> None:
        path = settings.documents_dir / "eda" / "eda_report.json"
        self.assertTrue(path.exists(), "Run `python -m notebooks.eda`")

    def test_feature_categories_exist(self) -> None:
        path = settings.documents_dir / "eda" / "feature_categories.json"
        self.assertTrue(path.exists(), "Run feature engineering or load EDA endpoint")

    def test_database_exists(self) -> None:
        self.assertTrue(
            settings.database_path.exists(),
            "Run `python -m src.database.build_database`",
        )

    def test_feature_store_exists(self) -> None:
        self.assertTrue(
            settings.feature_store_path.exists(),
            "Run `python -m src.data.feature_engineering`",
        )


class ApiSmokeTests(unittest.TestCase):
    """Exercise core HTTP endpoints through FastAPI TestClient."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_dashboard_kpis(self) -> None:
        response = self.client.get("/dashboard/kpis")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body.get("applicant_count", 0), 0)

    def test_eda_with_feature_categories(self) -> None:
        response = self.client.get("/eda")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("chart_urls", body)
        categories = body.get("feature_categories", {}).get("categories", [])
        self.assertGreaterEqual(len(categories), 5)

    def test_evaluation_endpoint(self) -> None:
        response = self.client.get("/evaluation")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("test_metrics", body)
        self.assertIn("roc_auc", body["test_metrics"])

    def test_eda_chart_asset(self) -> None:
        report = self.client.get("/eda").json()
        urls = report.get("chart_urls", [])
        if not urls:
            self.skipTest("No EDA chart URLs in report")
        response = self.client.get(urls[0])
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers.get("content-type", "").startswith("image/"))

    def test_shap_global(self) -> None:
        response = self.client.get("/shap/global")
        self.assertEqual(response.status_code, 200)
        self.assertIn("feature_importance", response.json())

    def test_global_rules(self) -> None:
        response = self.client.get("/rules")
        self.assertEqual(response.status_code, 200)
        self.assertIn("rules", response.json())

    @unittest.skipUnless(
        os.getenv("RUN_ML_SMOKE_TESTS", "").lower() in {"1", "true", "yes"},
        "Set RUN_ML_SMOKE_TESTS=1 to run prediction and explainability smoke tests.",
    )
    def test_predict_lookup(self) -> None:
        response = self.client.post("/predict/lookup", json={"identifier": "100002"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("overall_risk", body)
        self.assertIn("risk_band", body["overall_risk"])

    @unittest.skipUnless(
        os.getenv("RUN_ML_SMOKE_TESTS", "").lower() in {"1", "true", "yes"},
        "Set RUN_ML_SMOKE_TESTS=1 to run prediction and explainability smoke tests.",
    )
    def test_explain_customer(self) -> None:
        response = self.client.get("/explain/customer/100002")
        self.assertEqual(response.status_code, 200)
        explanations = response.json().get("explanations", [])
        self.assertTrue(explanations)
        first = explanations[0]
        self.assertIn("final_prediction", first)
        self.assertIn("stacking_shap", first)
        self.assertIn("feature_shap", first)
        self.assertIn("waterfall_chart_url", first)

    @unittest.skipUnless(
        os.getenv("RUN_GEMINI_TESTS", "").lower() in {"1", "true", "yes"}
        and bool(settings.gemini_api_key),
        "Set RUN_GEMINI_TESTS=1 and GEMINI_API_KEY for chat smoke test.",
    )
    def test_chat_with_business_insight(self) -> None:
        response = self.client.post(
            "/chat",
            json={"question": "How many customers are in each risk band?"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("sql", body)
        self.assertIn("rows", body)
        self.assertIn("business_insight", body)
        self.assertTrue(len(body["business_insight"]) > 20)

    def test_frontend_index_served(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Credit Risk Intelligence Platform", response.text)


if __name__ == "__main__":
    unittest.main()
