"""Exploratory data analysis for the Credit Risk Intelligence Platform."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("MPLCONFIGDIR", str(Path.cwd() / "documents" / ".matplotlib"))

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from src.data.loader import DataLoader
from src.utils.config import settings
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)
OUTPUT_DIR = settings.documents_dir / "eda"


def _save_plot(path: Path) -> None:
    """Save the active matplotlib plot and close it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=140, bbox_inches="tight")
    plt.close()


def generate_eda_outputs(sample_rows: int | None = settings.max_train_rows) -> Dict[str, object]:
    """Generate EDA charts, statistics, and business insights."""
    loader = DataLoader()
    app = loader.read_csv(settings.data_dir / "application_train.csv", nrows=sample_rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = app.isna().mean().sort_values(ascending=False).reset_index()
    missing.columns = ["column", "missing_rate"]
    missing.to_csv(OUTPUT_DIR / "missing_values.csv", index=False)

    target_distribution = app["TARGET"].value_counts(normalize=True).rename("rate").reset_index()
    target_distribution.columns = ["target", "rate"]
    target_distribution.to_csv(OUTPUT_DIR / "target_distribution.csv", index=False)

    charts: List[str] = []
    chart_specs = [
        ("target_distribution.png", lambda: sns.countplot(data=app, x="TARGET")),
        ("income_distribution.png", lambda: sns.histplot(app["AMT_INCOME_TOTAL"].clip(upper=1_000_000), bins=50)),
        ("credit_distribution.png", lambda: sns.histplot(app["AMT_CREDIT"], bins=50)),
        ("annuity_distribution.png", lambda: sns.histplot(app["AMT_ANNUITY"], bins=50)),
        ("age_distribution.png", lambda: sns.histplot((-app["DAYS_BIRTH"] / 365.25), bins=50)),
        ("gender_default_rate.png", lambda: sns.barplot(data=app, x="CODE_GENDER", y="TARGET")),
        ("education_default_rate.png", lambda: sns.barplot(data=app, x="NAME_EDUCATION_TYPE", y="TARGET")),
        ("occupation_default_rate.png", lambda: sns.barplot(data=app, x="OCCUPATION_TYPE", y="TARGET")),
        ("family_status_default_rate.png", lambda: sns.barplot(data=app, x="NAME_FAMILY_STATUS", y="TARGET")),
        ("housing_default_rate.png", lambda: sns.barplot(data=app, x="NAME_HOUSING_TYPE", y="TARGET")),
    ]

    for filename, plotter in chart_specs:
        plt.figure(figsize=(10, 5))
        plotter()
        plt.xticks(rotation=35, ha="right")
        _save_plot(OUTPUT_DIR / filename)
        charts.append(filename)

    numeric_columns = [
        "TARGET",
        "AMT_INCOME_TOTAL",
        "AMT_CREDIT",
        "AMT_ANNUITY",
        "DAYS_BIRTH",
        "DAYS_EMPLOYED",
        "CNT_CHILDREN",
    ]
    corr = app[numeric_columns].corr(numeric_only=True)
    plt.figure(figsize=(8, 6))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
    _save_plot(OUTPUT_DIR / "correlation_heatmap.png")
    charts.append("correlation_heatmap.png")

    insights = [
        f"Observed default rate is {app['TARGET'].mean():.2%}.",
        "The target is imbalanced, so PR-AUC and recall must be monitored with ROC-AUC.",
        "Income, credit amount, and annuity require robust imputation and scaling.",
        "Demographic default rates vary by education, occupation, housing, and family status.",
        "Historical bureau and repayment tables are required to explain repayment behavior beyond the application form.",
    ]
    report = {
        "rows_analyzed": int(len(app)),
        "columns_analyzed": int(app.shape[1]),
        "charts": charts,
        "business_insights": insights,
        "top_missing_columns": missing.head(20).to_dict(orient="records"),
        "target_distribution": target_distribution.to_dict(orient="records"),
    }
    write_json(report, OUTPUT_DIR / "eda_report.json")
    (OUTPUT_DIR / "business_insights.md").write_text(
        "# EDA Business Insights\n\n" + "\n".join(f"- {insight}" for insight in insights),
        encoding="utf-8",
    )
    logger.info("Generated EDA outputs in %s", OUTPUT_DIR)
    return report


def main() -> None:
    """Run EDA generation."""
    generate_eda_outputs()


if __name__ == "__main__":
    main()
