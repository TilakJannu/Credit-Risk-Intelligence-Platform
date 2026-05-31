"""Business-readable rule generation from model behavior."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import joblib
import pandas as pd
from sklearn.tree import DecisionTreeClassifier, _tree

from src.ml.evaluate import predict_probabilities
from src.utils.config import settings
from src.utils.helpers import write_json
from src.utils.logger import get_logger


logger = get_logger(__name__)


def train_surrogate_tree(
    x_train: pd.DataFrame,
    probabilities: pd.Series,
) -> DecisionTreeClassifier:
    """Train a shallow decision tree to approximate high-risk behavior."""
    labels = (probabilities > settings.high_risk_threshold).astype(int)
    tree = DecisionTreeClassifier(
        max_depth=4,
        min_samples_leaf=200,
        random_state=settings.random_state,
    )
    tree.fit(x_train, labels)
    joblib.dump(tree, settings.models_dir / "business_rule_tree.pkl")
    return tree


def extract_rules(tree: DecisionTreeClassifier, feature_names: List[str]) -> List[str]:
    """Extract readable IF/AND/THEN rules from a fitted decision tree."""
    tree_ = tree.tree_
    rules: List[str] = []

    def recurse(node: int, conditions: List[str]) -> None:
        if tree_.feature[node] != _tree.TREE_UNDEFINED:
            feature = feature_names[tree_.feature[node]]
            threshold = tree_.threshold[node]
            recurse(tree_.children_left[node], conditions + [f"{feature} <= {threshold:.3f}"])
            recurse(tree_.children_right[node], conditions + [f"{feature} > {threshold:.3f}"])
        else:
            class_id = int(tree_.value[node][0].argmax())
            if class_id == 1:
                rule = "IF " + "\nAND ".join(conditions) + "\nTHEN High Risk"
                rules.append(rule)

    recurse(0, [])
    return rules


def generate_business_rules(output_dir: Path = settings.documents_dir / "rules") -> Dict[str, object]:
    """Generate and persist business-readable high-risk rules."""
    output_dir.mkdir(parents=True, exist_ok=True)
    x_train = pd.read_parquet(settings.documents_dir / "processed" / "x_train_scored.parquet")
    probabilities = pd.Series(predict_probabilities(x_train))
    tree = train_surrogate_tree(x_train, probabilities)
    rules = extract_rules(tree, x_train.columns.tolist())
    payload = {"rules": rules}
    write_json(payload, output_dir / "business_rules.json")
    (output_dir / "business_rules.md").write_text(
        "# Business Risk Rules\n\n" + "\n\n".join(f"```text\n{rule}\n```" for rule in rules),
        encoding="utf-8",
    )
    logger.info("Generated %s high-risk business rules", len(rules))
    return payload
