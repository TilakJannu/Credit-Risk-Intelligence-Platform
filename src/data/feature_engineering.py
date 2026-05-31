"""Feature engineering for Home Credit applicant-level modeling.

The functions in this module preserve business meaning by creating
explainable aggregates from bureau, repayment, credit card, POS, and
previous-application history. The output is one row per `SK_ID_CURR`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from src.data.feature_categories import write_feature_categories
from src.data.loader import DataLoader
from src.utils.config import settings
from src.utils.logger import get_logger


logger = get_logger(__name__)


def _flatten_columns(frame: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Flatten grouped aggregation columns and apply a source prefix."""
    frame.columns = [
        f"{prefix}_{'_'.join(str(part) for part in column if part)}".upper()
        if isinstance(column, tuple)
        else f"{prefix}_{column}".upper()
        for column in frame.columns
    ]
    return frame.reset_index()


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Return a numerically stable ratio with missing invalid denominators."""
    denominator = denominator.replace(0, np.nan)
    return numerator / denominator


def _aggregate_numeric(
    frame: pd.DataFrame,
    group_key: str,
    prefix: str,
    excluded: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Aggregate numeric columns by key using common credit-risk statistics."""
    excluded_columns = set(excluded or [])
    numeric_columns = [
        column
        for column in frame.select_dtypes(include=[np.number]).columns
        if column != group_key and column not in excluded_columns
    ]
    if not numeric_columns:
        return frame[[group_key]].drop_duplicates()
    grouped = frame.groupby(group_key)[numeric_columns].agg(["mean", "max", "min", "sum", "std"])
    return _flatten_columns(grouped, prefix)


def build_bureau_features(
    bureau: pd.DataFrame,
    bureau_balance: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """Create bureau history features at applicant level."""
    bureau = bureau.copy()
    bureau["BUREAU_IS_ACTIVE"] = (bureau["CREDIT_ACTIVE"] == "Active").astype(int)
    bureau["BUREAU_IS_CLOSED"] = (bureau["CREDIT_ACTIVE"] == "Closed").astype(int)
    bureau["BUREAU_OVERDUE_FLAG"] = (bureau["CREDIT_DAY_OVERDUE"].fillna(0) > 0).astype(int)
    bureau["BUREAU_DEBT_TO_CREDIT_RATIO"] = _safe_ratio(
        bureau["AMT_CREDIT_SUM_DEBT"].fillna(0),
        bureau["AMT_CREDIT_SUM"].fillna(0),
    )
    bureau["BUREAU_OVERDUE_TO_CREDIT_RATIO"] = _safe_ratio(
        bureau["AMT_CREDIT_SUM_OVERDUE"].fillna(0),
        bureau["AMT_CREDIT_SUM"].fillna(0),
    )

    features = _aggregate_numeric(
        bureau,
        "SK_ID_CURR",
        "bureau",
        excluded=["SK_ID_BUREAU"],
    )
    status_counts = (
        bureau.groupby(["SK_ID_CURR", "CREDIT_ACTIVE"])
        .size()
        .unstack(fill_value=0)
        .add_prefix("BUREAU_STATUS_COUNT_")
        .reset_index()
    )
    features = features.merge(status_counts, on="SK_ID_CURR", how="left")

    if bureau_balance is not None and not bureau_balance.empty:
        balance = bureau_balance.copy()
        balance["BUREAU_BALANCE_BAD_STATUS"] = balance["STATUS"].isin(["1", "2", "3", "4", "5"]).astype(int)
        balance_features = _aggregate_numeric(balance, "SK_ID_BUREAU", "bureau_balance")
        linked = bureau[["SK_ID_CURR", "SK_ID_BUREAU"]].merge(
            balance_features,
            on="SK_ID_BUREAU",
            how="left",
        )
        linked_features = _aggregate_numeric(
            linked,
            "SK_ID_CURR",
            "bureau_balance",
            excluded=["SK_ID_BUREAU"],
        )
        features = features.merge(linked_features, on="SK_ID_CURR", how="left")

    return features


def build_installment_features(installments: pd.DataFrame) -> pd.DataFrame:
    """Create repayment behavior features from installment history."""
    frame = installments.copy()
    frame["INSTALLMENT_PAYMENT_DELAY"] = frame["DAYS_ENTRY_PAYMENT"] - frame["DAYS_INSTALMENT"]
    frame["INSTALLMENT_LATE_PAYMENT_FLAG"] = (frame["INSTALLMENT_PAYMENT_DELAY"].fillna(0) > 0).astype(int)
    frame["INSTALLMENT_PAYMENT_RATIO"] = _safe_ratio(frame["AMT_PAYMENT"], frame["AMT_INSTALMENT"])
    frame["INSTALLMENT_UNDERPAYMENT_FLAG"] = (frame["INSTALLMENT_PAYMENT_RATIO"].fillna(1) < 1).astype(int)
    return _aggregate_numeric(frame, "SK_ID_CURR", "installment", excluded=["SK_ID_PREV"])


def build_credit_card_features(credit_card: pd.DataFrame) -> pd.DataFrame:
    """Create credit utilization and delinquency features from credit cards."""
    frame = credit_card.copy()
    frame["CC_UTILIZATION_RATIO"] = _safe_ratio(
        frame["AMT_BALANCE"].fillna(0),
        frame["AMT_CREDIT_LIMIT_ACTUAL"].fillna(0),
    )
    frame["CC_PAYMENT_RATIO"] = _safe_ratio(
        frame["AMT_PAYMENT_CURRENT"].fillna(0),
        frame["AMT_INST_MIN_REGULARITY"].fillna(0),
    )
    frame["CC_DPD_FLAG"] = (frame["SK_DPD"].fillna(0) > 0).astype(int)
    frame["CC_DEFAULT_DPD_FLAG"] = (frame["SK_DPD_DEF"].fillna(0) > 0).astype(int)
    return _aggregate_numeric(frame, "SK_ID_CURR", "credit_card", excluded=["SK_ID_PREV"])


def build_pos_features(pos_cash: pd.DataFrame) -> pd.DataFrame:
    """Create point-of-sale cash loan behavior features."""
    frame = pos_cash.copy()
    frame["POS_DPD_FLAG"] = (frame["SK_DPD"].fillna(0) > 0).astype(int)
    frame["POS_DEFAULT_DPD_FLAG"] = (frame["SK_DPD_DEF"].fillna(0) > 0).astype(int)
    frame["POS_INSTALLMENT_COMPLETION_RATIO"] = _safe_ratio(
        frame["CNT_INSTALMENT"] - frame["CNT_INSTALMENT_FUTURE"],
        frame["CNT_INSTALMENT"],
    )
    return _aggregate_numeric(frame, "SK_ID_CURR", "pos", excluded=["SK_ID_PREV"])


def build_previous_application_features(previous: pd.DataFrame) -> pd.DataFrame:
    """Create loan history features from previous applications."""
    frame = previous.copy()
    frame["PREV_APPROVED_FLAG"] = (frame["NAME_CONTRACT_STATUS"] == "Approved").astype(int)
    frame["PREV_REJECTED_FLAG"] = (frame["NAME_CONTRACT_STATUS"] == "Refused").astype(int)
    frame["PREV_CREDIT_TO_APPLICATION_RATIO"] = _safe_ratio(
        frame["AMT_CREDIT"].fillna(0),
        frame["AMT_APPLICATION"].fillna(0),
    )
    frame["PREV_DOWN_PAYMENT_RATIO"] = _safe_ratio(
        frame["AMT_DOWN_PAYMENT"].fillna(0),
        frame["AMT_CREDIT"].fillna(0),
    )
    return _aggregate_numeric(frame, "SK_ID_CURR", "previous", excluded=["SK_ID_PREV"])


def build_application_features(application: pd.DataFrame) -> pd.DataFrame:
    """Create business-ratio features from the current application table."""
    frame = application.copy()
    frame["APP_CREDIT_TO_INCOME_RATIO"] = _safe_ratio(frame["AMT_CREDIT"], frame["AMT_INCOME_TOTAL"])
    frame["APP_ANNUITY_TO_INCOME_RATIO"] = _safe_ratio(frame["AMT_ANNUITY"], frame["AMT_INCOME_TOTAL"])
    frame["APP_GOODS_TO_CREDIT_RATIO"] = _safe_ratio(frame["AMT_GOODS_PRICE"], frame["AMT_CREDIT"])
    frame["APP_EMPLOYMENT_YEARS"] = (-frame["DAYS_EMPLOYED"].replace(365243, np.nan)) / 365.25
    frame["APP_AGE_YEARS"] = (-frame["DAYS_BIRTH"]) / 365.25
    return frame


def build_feature_store(
    datasets: Dict[str, pd.DataFrame],
    output_path: Path = settings.feature_store_path,
) -> pd.DataFrame:
    """Build and persist an applicant-level feature store.

    Args:
        datasets: Raw Home Credit datasets keyed by filename.
        output_path: Destination parquet path.

    Returns:
        Applicant-level feature DataFrame with `TARGET` when available.
    """
    application = build_application_features(datasets["application_train.csv"])
    features = application

    feature_builders = [
        build_bureau_features(
            datasets["bureau.csv"],
            datasets.get("bureau_balance.csv"),
        ),
        build_previous_application_features(datasets["previous_application.csv"]),
        build_installment_features(datasets["installments_payments.csv"]),
        build_credit_card_features(datasets["credit_card_balance.csv"]),
        build_pos_features(datasets["POS_CASH_balance.csv"]),
    ]

    for derived in feature_builders:
        features = features.merge(derived, on="SK_ID_CURR", how="left")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    features.to_parquet(output_path, index=False)
    write_feature_categories(features.columns.tolist())
    logger.info(
        "Wrote feature store to %s with shape %s",
        output_path,
        features.shape,
    )
    return features


def main() -> None:
    """Generate the feature store from configured Home Credit files."""
    datasets = DataLoader().load_training_sources(nrows=settings.max_train_rows)
    build_feature_store(datasets)


if __name__ == "__main__":
    main()
