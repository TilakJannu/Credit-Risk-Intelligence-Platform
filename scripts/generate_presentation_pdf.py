"""Generate documents/project_presentation.pdf for NeoStats submission."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os_env = __import__("os").environ
os_env.setdefault("MPLCONFIGDIR", str(_REPO_ROOT / "documents" / ".matplotlib"))

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from src.utils.config import settings


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _text_page(pdf: PdfPages, title: str, lines: list[str]) -> None:
    figure = plt.figure(figsize=(11, 8.5))
    figure.patch.set_facecolor("white")
    text = f"{title}\n\n" + "\n".join(lines)
    figure.text(0.08, 0.92, text, va="top", ha="left", fontsize=11, family="monospace")
    plt.axis("off")
    pdf.savefig(figure, bbox_inches="tight")
    plt.close(figure)


def _image_page(pdf: PdfPages, title: str, image_path: Path) -> None:
    if not image_path.exists():
        _text_page(pdf, title, [f"Image not found: {image_path.name}"])
        return
    figure = plt.figure(figsize=(11, 8.5))
    img = plt.imread(image_path)
    plt.imshow(img)
    plt.axis("off")
    plt.title(title, fontsize=14)
    pdf.savefig(figure, bbox_inches="tight")
    plt.close(figure)


def main() -> int:
    """Build a submission-ready PDF with metrics and chart screenshots."""
    output = settings.documents_dir / "project_presentation.pdf"
    evaluation = _load_json(settings.documents_dir / "evaluation" / "evaluation_report.json")
    eda = _load_json(settings.documents_dir / "eda" / "eda_report.json")

    with PdfPages(output) as pdf:
        _text_page(
            pdf,
            "Credit Risk Intelligence Platform",
            [
                "NeoStats AI Engineer Assignment — Submission Deck (auto-generated baseline)",
                "",
                "Replace or extend this PDF with your own branded slides and UI screenshots.",
                "",
                "Architecture: Home Credit data → feature store → stacking ensemble → SHAP/LIME",
                "→ SQLite → Talk-to-Data (Gemini or offline fallback) → FastAPI dashboard → Docker",
                "",
                f"Applicants analyzed (EDA): {eda.get('rows_analyzed', 'N/A')}",
                f"Engineered feature categories: {len(_load_json(settings.documents_dir / 'eda' / 'feature_categories.json').get('categories', []))}",
                "",
                "Test metrics (stacking ensemble):",
                f"  ROC-AUC: {evaluation.get('roc_auc', 'N/A')}",
                f"  PR-AUC:  {evaluation.get('pr_auc', 'N/A')}",
                f"  Recall:  {evaluation.get('recall', 'N/A')}",
                f"  F1:      {evaluation.get('f1', 'N/A')}",
                "",
                "Risk bands: LOW < 0.30 | MEDIUM 0.30–0.60 | HIGH > 0.60",
            ],
        )

        chart_sets = [
            ("EDA — Target distribution", settings.documents_dir / "eda" / "target_distribution.png"),
            ("EDA — Income distribution", settings.documents_dir / "eda" / "income_distribution.png"),
            ("Evaluation — ROC curve", settings.documents_dir / "evaluation" / "roc_curve.png"),
            ("Evaluation — PR curve", settings.documents_dir / "evaluation" / "pr_curve.png"),
            ("Evaluation — Confusion matrix", settings.documents_dir / "evaluation" / "confusion_matrix.png"),
            ("SHAP — Global summary", settings.documents_dir / "shap" / "shap_summary.png"),
        ]
        for title, path in chart_sets:
            _image_page(pdf, title, path)

        _text_page(
            pdf,
            "Talk-to-Data & Explainability",
            [
                "Talk-to-Data: NL → validated SQL → rows → business insight",
                "  • Gemini mode when GEMINI_API_KEY is set",
                "  • Offline fallback for 7 verified catalog questions",
                "",
                "Explainability:",
                "  • Stacking SHAP (meta-learner on base model probabilities)",
                "  • Feature SHAP (XGBoost) + official shap.plots.waterfall PNG",
                "  • LIME (stacking black-box)",
                "",
                "Run: uvicorn src.api.main:app --port 8000",
                "Docker: docker-compose up --build",
            ],
        )

    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
