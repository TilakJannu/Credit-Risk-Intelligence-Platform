"""FastAPI application for the Credit Risk Intelligence Platform."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from src.data.feature_categories import load_or_build_feature_categories
from src.database.db_manager import DatabaseManager
from src.explainability.explanation_service import ExplanationService
from src.ml.predict import predict_from_records
from src.talk_to_data.service import TalkToDataService
from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)
app = FastAPI(title="Credit Risk Intelligence Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PredictionRequest(BaseModel):
    """Prediction request payload."""

    applicants: List[Dict[str, Any]] = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Talk-to-Data chat request payload."""

    question: str = Field(..., min_length=3)


class LookupRequest(BaseModel):
    """Customer lookup request payload."""

    identifier: str = Field(..., min_length=1)


@app.on_event("startup")
def _startup() -> None:
    """Initialize database schema on application startup."""
    DatabaseManager().initialize()


@app.get("/health")
def health() -> Dict[str, str]:
    """Return service health status."""
    return {"status": "ok"}


@lru_cache(maxsize=1)
def _feature_store() -> pd.DataFrame:
    """Load the applicant-level feature store once per API process."""
    if not settings.feature_store_path.exists():
        raise FileNotFoundError(
            f"Feature store not found at {settings.feature_store_path}. "
            "Run `python -m src.data.feature_engineering` first.",
        )
    return pd.read_parquet(settings.feature_store_path)


def _customer_by_id(customer_id: int) -> pd.DataFrame:
    """Return a one-row feature frame for a customer ID."""
    frame = _feature_store()
    customer = frame.loc[frame["SK_ID_CURR"] == customer_id]
    if customer.empty:
        raise HTTPException(status_code=404, detail=f"Customer ID {customer_id} was not found.")
    return customer.head(1).copy()


def _customer_by_identifier(identifier: str) -> pd.DataFrame:
    """Return a customer row by ID, with a clear message for unsupported names."""
    value = identifier.strip()
    if value.isdigit():
        return _customer_by_id(int(value))
    raise HTTPException(
        status_code=400,
        detail=(
            "Name lookup is not available because the Home Credit dataset does not "
            "contain applicant names. Use SK_ID_CURR/customer ID instead."
        ),
    )


def _response_with_overall_risk(predictions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Attach an overall risk summary to a prediction response."""
    if not predictions:
        return {"predictions": [], "overall_risk": None}
    highest = max(predictions, key=lambda item: float(item["default_probability"]))
    return {
        "predictions": predictions,
        "overall_risk": {
            "customer_id": highest.get("customer_id"),
            "default_probability": highest["default_probability"],
            "risk_score": highest["risk_score"],
            "risk_band": highest["risk_band"],
        },
    }


def _explain_payload(customer: pd.DataFrame) -> Dict[str, Any]:
    """Build unified explainability payload for one or more applicants."""
    service = ExplanationService()
    explanations = service.explain_applicants(customer)
    for index, row in enumerate(explanations):
        applicant = customer.iloc[[index]]
        cid = explanations[index].get("customer_id")
        explanations[index]["waterfall_chart_url"] = service.save_waterfall_plot(
            applicant,
            customer_id=int(cid) if cid is not None else None,
        )
    return {"explanations": explanations}


def _specific_rules(customer: pd.DataFrame) -> Dict[str, Any]:
    """Generate customer-specific business rules from prediction and SHAP drivers."""
    predictions = predict_from_records(customer.to_dict(orient="records"))
    explanation = ExplanationService().explain_applicants(customer, include_lime=False)[0]
    overall = _response_with_overall_risk(predictions)["overall_risk"]
    positive = explanation["feature_shap"]["top_positive_contributors"]
    negative = explanation["feature_shap"]["top_negative_contributors"]
    
    rules = []
    # High Risk Rules: strong positive contributors
    for item in positive:
        val = float(item["shap_value"])
        if val > 0.05:
            rules.append(
                f"IF {item['feature']} contributes {val:.4f} "
                f"to this applicant's default risk THEN High Risk"
            )
            
    # Medium Risk Rules: moderate positive/negative contributors
    for item in positive:
        val = float(item["shap_value"])
        if 0 < val <= 0.05:
            rules.append(
                f"IF {item['feature']} contributes {val:.4f} "
                f"to this applicant's default risk THEN Medium Risk"
            )
    for item in negative:
        val = float(item["shap_value"])
        if -0.05 <= val < 0:
            rules.append(
                f"IF {item['feature']} contributes {val:.4f} "
                f"to this applicant's default risk THEN Medium Risk"
            )
            
    # Low Risk Rules: strong negative contributors (mitigants)
    for item in negative:
        val = float(item["shap_value"])
        if val < -0.05:
            rules.append(
                f"IF {item['feature']} contributes {val:.4f} "
                f"to this applicant's default risk THEN Low Risk"
            )
            
    if not rules:
        rules = [f"IF model probability is {overall['default_probability']:.2%} THEN {overall['risk_band']} Risk"]
        
    return {
        "customer_id": overall["customer_id"],
        "overall_risk": overall,
        "rules": rules,
        "top_risk_drivers": positive,
    }


@app.post("/predict")
def predict(request: PredictionRequest) -> Dict[str, Any]:
    """Generate risk predictions for applicant records."""
    try:
        predictions = predict_from_records(request.applicants)
        DatabaseManager().insert_predictions(predictions)
        return _response_with_overall_risk(predictions)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/predict/lookup")
def predict_lookup(request: LookupRequest) -> Dict[str, Any]:
    """Predict risk by customer ID from the existing feature store."""
    customer = _customer_by_identifier(request.identifier)
    predictions = predict_from_records(customer.to_dict(orient="records"))
    DatabaseManager().insert_predictions(predictions)
    response = _response_with_overall_risk(predictions)
    response["lookup"] = {"identifier": request.identifier, "matched_by": "SK_ID_CURR"}
    return response


@app.get("/predict/customer/{customer_id}")
def predict_customer(customer_id: int) -> Dict[str, Any]:
    """Predict risk by customer ID."""
    customer = _customer_by_id(customer_id)
    predictions = predict_from_records(customer.to_dict(orient="records"))
    DatabaseManager().insert_predictions(predictions)
    return _response_with_overall_risk(predictions)


@app.post("/explain")
def explain(request: PredictionRequest) -> Dict[str, Any]:
    """Generate stacking-aligned SHAP, LIME, and waterfall explanations."""
    try:
        return _explain_payload(pd.DataFrame.from_records(request.applicants))
    except Exception as exc:
        logger.exception("Explainability failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/explain/customer/{customer_id}")
def explain_customer(customer_id: int) -> Dict[str, Any]:
    """Generate full explanations for a customer ID."""
    return _explain_payload(_customer_by_id(customer_id))


@app.get("/assets/explainability/{filename}")
def explainability_asset(filename: str) -> FileResponse:
    """Serve generated SHAP waterfall PNG files."""
    safe_name = _safe_asset_filename(filename)
    if not safe_name.startswith("waterfall_") or not safe_name.endswith(".png"):
        raise HTTPException(status_code=404, detail="Unknown explainability asset.")
    asset_path = settings.documents_dir / "explainability" / "waterfalls" / safe_name
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail=f"Waterfall chart '{safe_name}' not found.")
    return FileResponse(asset_path)


@app.get("/rules")
def rules(customer_id: Optional[int] = None) -> Dict[str, Any]:
    """Return generated business rules."""
    if customer_id is not None:
        return _specific_rules(_customer_by_id(customer_id))
    path = settings.documents_dir / "rules" / "business_rules.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"rules": []}


@app.get("/rules/customer/{customer_id}")
def customer_rules(customer_id: int) -> Dict[str, Any]:
    """Return customer-specific risk rules."""
    return _specific_rules(_customer_by_id(customer_id))


@app.post("/rules/customer")
def customer_rules_from_payload(request: PredictionRequest) -> Dict[str, Any]:
    """Return customer-specific risk rules from applicant JSON."""
    try:
        customer = pd.DataFrame.from_records(request.applicants).head(1)
        return _specific_rules(customer)
    except Exception as exc:
        logger.exception("Customer-specific rule generation failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _safe_asset_filename(filename: str) -> str:
    """Reject path traversal and non-image asset names."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.(png|csv|json)", filename):
        raise HTTPException(status_code=400, detail="Invalid asset filename.")
    return filename


def _eda_chart_filenames() -> List[str]:
    """Return whitelisted EDA chart filenames from the generated report."""
    report_path = settings.documents_dir / "eda" / "eda_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        return [str(name) for name in report.get("charts", [])]
    return []


def _kpis_from_eda_report() -> Dict[str, Any]:
    """Build dashboard KPIs from the offline EDA report when SQLite is empty."""
    path = settings.documents_dir / "eda" / "eda_report.json"
    if not path.exists():
        return {
            "applicant_count": 0,
            "default_rate": None,
            "risk_distribution": [],
            "predictions_scored": 0,
            "source": "none",
        }
    report = json.loads(path.read_text(encoding="utf-8"))
    default_rate = None
    for item in report.get("target_distribution", []):
        if int(item.get("target", -1)) == 1:
            default_rate = float(item.get("rate", 0))
            break
    return {
        "applicant_count": int(report.get("rows_analyzed", 0)),
        "default_rate": default_rate,
        "risk_distribution": [],
        "predictions_scored": 0,
        "source": "eda",
    }


@app.get("/dashboard/kpis")
def dashboard_kpis() -> Dict[str, Any]:
    """Return live executive dashboard metrics from SQLite with EDA fallback."""
    manager = DatabaseManager()
    try:
        with manager.connect(read_only=True) as connection:
            applicant_row = connection.execute("SELECT COUNT(*) FROM customers").fetchone()
            applicant_count = int(applicant_row[0]) if applicant_row else 0
            default_row = connection.execute(
                "SELECT AVG(target) FROM customers WHERE target IS NOT NULL",
            ).fetchone()
            default_rate = float(default_row[0]) if default_row and default_row[0] is not None else None
            prediction_rows = connection.execute("SELECT COUNT(*) FROM predictions").fetchone()
            predictions_scored = int(prediction_rows[0]) if prediction_rows else 0
            risk_rows = connection.execute(
                """
                SELECT risk_band, COUNT(*) AS count
                FROM predictions
                GROUP BY risk_band
                ORDER BY risk_band
                """,
            ).fetchall()
    except Exception as exc:
        logger.warning("Dashboard KPI query failed: %s", exc)
        payload = _kpis_from_eda_report()
        payload["message"] = "Database unavailable; showing EDA fallback metrics."
        return payload

    if applicant_count == 0 and predictions_scored == 0:
        payload = _kpis_from_eda_report()
        payload["message"] = "Database is empty; showing EDA fallback metrics."
        return payload

    total_risk = sum(int(row[1]) for row in risk_rows) or 1
    risk_distribution = [
        {
            "band": str(row[0]),
            "count": int(row[1]),
            "pct": round(int(row[1]) / total_risk * 100, 2),
        }
        for row in risk_rows
    ]
    return {
        "applicant_count": applicant_count,
        "default_rate": default_rate,
        "risk_distribution": risk_distribution,
        "predictions_scored": predictions_scored,
        "source": "database",
    }


@app.get("/assets/eda/{filename}")
def eda_asset(filename: str) -> FileResponse:
    """Serve a generated EDA chart from the documents directory."""
    safe_name = _safe_asset_filename(filename)
    allowed = set(_eda_chart_filenames())
    if allowed and safe_name not in allowed:
        raise HTTPException(status_code=404, detail=f"Chart '{safe_name}' is not in the EDA report.")
    asset_path = settings.documents_dir / "eda" / safe_name
    if not asset_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Chart '{safe_name}' not found. Run `python -m notebooks.eda` to generate it.",
        )
    return FileResponse(asset_path)


@app.get("/assets/shap/{filename}")
def shap_asset(filename: str) -> FileResponse:
    """Serve a generated SHAP artifact image from the documents directory."""
    safe_name = _safe_asset_filename(filename)
    allowed = {"shap_summary.png"}
    if safe_name not in allowed:
        raise HTTPException(status_code=404, detail=f"SHAP asset '{safe_name}' is not available.")
    asset_path = settings.documents_dir / "shap" / safe_name
    if not asset_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"SHAP asset '{safe_name}' not found. Generate SHAP outputs after model training.",
        )
    return FileResponse(asset_path)


@app.get("/shap/global")
def shap_global() -> Dict[str, Any]:
    """Return global SHAP feature importance and summary chart URL."""
    importance_path = settings.documents_dir / "shap" / "feature_importance.csv"
    features: List[Dict[str, object]] = []
    if importance_path.exists():
        frame = pd.read_csv(importance_path).head(20)
        features = frame.to_dict(orient="records")
    summary_path = settings.documents_dir / "shap" / "shap_summary.png"
    return {
        "feature_importance": features,
        "summary_chart_url": "/assets/shap/shap_summary.png" if summary_path.exists() else None,
    }


EVALUATION_CHARTS = ("roc_curve.png", "pr_curve.png", "confusion_matrix.png")


def _load_json_if_exists(path: Path) -> Optional[Dict[str, Any]]:
    """Load a JSON object from disk when the file exists."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/evaluation")
def evaluation() -> Dict[str, Any]:
    """Return model evaluation metrics, validation scores, and chart URLs."""
    eval_dir = settings.documents_dir / "evaluation"
    test_metrics = _load_json_if_exists(eval_dir / "evaluation_report.json")
    base_validation = _load_json_if_exists(settings.models_dir / "base_model_validation_metrics.json")
    stacking_validation = _load_json_if_exists(settings.models_dir / "stacking_validation_metrics.json")
    metadata = _load_json_if_exists(settings.models_dir / "model_metadata.json")
    chart_urls = {
        name: f"/assets/evaluation/{name}"
        for name in EVALUATION_CHARTS
        if (eval_dir / name).exists()
    }
    if not test_metrics and not base_validation:
        return {"message": "Evaluation report has not been generated yet. Run `python -m src.ml.evaluate`."}
    return {
        "test_metrics": test_metrics,
        "base_model_validation": base_validation,
        "stacking_validation": stacking_validation,
        "model_metadata": metadata,
        "chart_urls": chart_urls,
        "risk_policy": {
            "low_risk_threshold": settings.low_risk_threshold,
            "high_risk_threshold": settings.high_risk_threshold,
            "low_band": f"probability < {settings.low_risk_threshold:.2f}",
            "medium_band": (
                f"{settings.low_risk_threshold:.2f} <= probability <= {settings.high_risk_threshold:.2f}"
            ),
            "high_band": f"probability > {settings.high_risk_threshold:.2f}",
        },
        "class_imbalance_strategy": [
            "Balanced class weights for Logistic Regression and Random Forest",
            "scale_pos_weight for XGBoost based on training default rate",
            "Stratified train/validation/test splits",
            "PR-AUC and recall tracked alongside ROC-AUC",
        ],
    }


@app.get("/assets/evaluation/{filename}")
def evaluation_asset(filename: str) -> FileResponse:
    """Serve generated evaluation plots from the documents directory."""
    safe_name = _safe_asset_filename(filename)
    if safe_name not in EVALUATION_CHARTS:
        raise HTTPException(status_code=404, detail=f"Evaluation asset '{safe_name}' is not available.")
    asset_path = settings.documents_dir / "evaluation" / safe_name
    if not asset_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Evaluation chart '{safe_name}' not found. Run `python -m src.ml.evaluate`.",
        )
    return FileResponse(asset_path)


@app.get("/eda")
def eda() -> Dict[str, Any]:
    """Return generated EDA report."""
    path = settings.documents_dir / "eda" / "eda_report.json"
    if path.exists():
        report = json.loads(path.read_text(encoding="utf-8"))
        charts = [str(name) for name in report.get("charts", [])]
        report["chart_urls"] = [f"/assets/eda/{name}" for name in charts]
        report["feature_categories"] = load_or_build_feature_categories()
        return report
    return {"message": "EDA report has not been generated yet."}


@app.post("/chat")
def chat(request: ChatRequest) -> Dict[str, Any]:
    """Answer a natural-language analytics question through NL-to-SQL."""
    try:
        result = TalkToDataService().ask(request.question)
        response: Dict[str, Any] = {
            "question": result.question,
            "sql": result.sql,
            "rows": result.rows,
            "row_count": result.row_count,
            "business_insight": result.business_insight,
            "mode": result.mode,
        }
        if result.insight_rows_used is not None:
            response["insight_rows_used"] = result.insight_rows_used
        if result.insight_error:
            response["insight_error"] = result.insight_error
        return response
    except Exception as exc:
        logger.exception("Talk-to-Data query failed")
        raise HTTPException(status_code=400, detail=str(exc)) from exc


static_dir = Path(__file__).resolve().parents[1] / "frontend" / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
