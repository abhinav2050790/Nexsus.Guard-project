"""Feature engineering and preprocessing pipeline.

ChargebackPreprocessor fits all data-derived statistics (amount quartiles,
trust-score scale, category encodings, scaler) on the training split only,
then deterministically transforms validation/test splits — preventing
target leakage from engineered features.
"""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

MODULE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = MODULE_DIR.parent

AMOUNT_TIER_LABELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
AMOUNT_TIER_ENCODED = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
DAY_BUCKET_LABELS = ["FRESH", "MEDIUM", "OLD", "STALE"]
DAY_BUCKET_ENCODED = {"FRESH": 0, "MEDIUM": 1, "OLD": 2, "STALE": 3}
REASON_CODE_ENCODED = {"CB001": 0, "CB002": 1, "CB003": 2, "CB004": 3}
PAYMENT_METHOD_RISK = {
    "card_credit": 0.3,
    "card_debit": 0.4,
    "upi": 0.6,
    "netbanking": 0.5,
    "wallet": 0.25,
}

VERIFICATION_WEIGHTS = {"is_3ds_verified": 0.40, "avs_match": 0.35, "cvv_match": 0.25}
HIGH_AMOUNT_THRESHOLD_INR = 15000.0
CHARGEBACK_RISK_MIN_COUNT = 3

SCALED_NUMERIC_COLUMNS = [
    "transaction_amount_inr",
    "days_since_transaction",
    "customer_account_age_days",
    "previous_orders_count",
    "previous_chargebacks_count",
    "evidence_completeness_score",
    "merchant_historical_win_rate",
    "reason_code_historical_win_rate",
    "customer_trust_score",
    "verification_score",
    "payment_method_risk",
]

FEATURE_COLUMNS = [
    "transaction_amount_inr",
    "high_amount_flag",
    "amount_risk_tier_encoded",
    "customer_trust_score",
    "is_first_time_buyer",
    "is_high_value_customer",
    "previous_orders_count",
    "previous_chargebacks_count",
    "chargeback_risk_flag",
    "days_since_transaction",
    "days_since_bucket_encoded",
    "is_3ds_verified",
    "avs_match",
    "cvv_match",
    "verification_score",
    "has_delivery_confirmation",
    "has_signed_receipt",
    "has_login_after_purchase",
    "has_support_interaction",
    "order_confirmation_sent",
    "refund_policy_acknowledged",
    "evidence_completeness_score",
    "merchant_historical_win_rate",
    "reason_code_historical_win_rate",
    "payment_method_risk",
    "merchant_category_encoded",
    "reason_code_encoded",
]

EXCLUDED_COLUMNS = {
    "transaction_id",
    "customer_id",
    "transaction_date",
    "payment_method",
    "merchant_category",
    "chargeback_reason_code",
    "amount_risk_tier",
    "days_since_bucket",
    "win_outcome",
    "split",
}


class ChargebackPreprocessor:
    """Fit-on-train / transform-anywhere feature engineering pipeline."""

    def __init__(self) -> None:
        self.amount_edges_: np.ndarray | None = None
        self.trust_scale_: float | None = None
        self.merchant_mapping_: dict[str, int] | None = None
        self.scaler_: StandardScaler | None = None
        self.feature_columns_: list[str] = list(FEATURE_COLUMNS)
        self._fitted: bool = False

    # ------------------------------------------------------------- loading

    def load_data(
        self, filepath: str | Path
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        df = pd.read_csv(filepath, parse_dates=["transaction_date"])
        train = df[df["split"] == "train"].reset_index(drop=True)
        val = df[df["split"] == "val"].reset_index(drop=True)
        test = df[df["split"] == "test"].reset_index(drop=True)
        return train, val, test

    # ---------------------------------------------------------- engineering

    def engineer_features(self, df: pd.DataFrame, fit: bool = False) -> pd.DataFrame:
        out = df.copy()

        if fit or self.amount_edges_ is None:
            q = out["transaction_amount_inr"].quantile([0.25, 0.50, 0.75]).to_numpy()
            self.amount_edges_ = q
        edges = self.amount_edges_
        out["amount_risk_tier"] = pd.cut(
            out["transaction_amount_inr"],
            bins=[-np.inf, edges[0], edges[1], edges[2], np.inf],
            labels=AMOUNT_TIER_LABELS,
        )

        trust_raw = out["previous_orders_count"] / (
            out["previous_chargebacks_count"] + 1.0
        )
        if fit or self.trust_scale_ is None:
            self.trust_scale_ = float(trust_raw.max()) or 1.0
        out["customer_trust_score"] = np.clip(
            trust_raw / self.trust_scale_, 0.0, 1.0
        )

        days = out["days_since_transaction"]
        out["days_since_bucket"] = np.select(
            [days < 30, days < 60, days < 90],
            ["FRESH", "MEDIUM", "OLD"],
            default="STALE",
        )

        out["verification_score"] = (
            VERIFICATION_WEIGHTS["is_3ds_verified"] * out["is_3ds_verified"].astype(float)
            + VERIFICATION_WEIGHTS["avs_match"] * out["avs_match"].astype(float)
            + VERIFICATION_WEIGHTS["cvv_match"] * out["cvv_match"].astype(float)
        )

        out["chargeback_risk_flag"] = (
            out["previous_chargebacks_count"] >= CHARGEBACK_RISK_MIN_COUNT
        )
        out["is_first_time_buyer"] = out["previous_orders_count"] == 0
        out["high_amount_flag"] = (
            out["transaction_amount_inr"] > HIGH_AMOUNT_THRESHOLD_INR
        )
        out["payment_method_risk"] = (
            out["payment_method"].map(PAYMENT_METHOD_RISK).astype(float).fillna(0.40)
        )
        out["reason_code_encoded"] = (
            out["chargeback_reason_code"].map(REASON_CODE_ENCODED).fillna(-1).astype(int)
        )
        out["amount_risk_tier_encoded"] = (
            out["amount_risk_tier"].astype(str).map(AMOUNT_TIER_ENCODED).fillna(-1).astype(int)
        )
        out["days_since_bucket_encoded"] = (
            out["days_since_bucket"].map(DAY_BUCKET_ENCODED).fillna(-1).astype(int)
        )

        if fit or self.merchant_mapping_ is None:
            cats = sorted(out["merchant_category"].astype(str).unique())
            self.merchant_mapping_ = {c: i for i, c in enumerate(cats)}
        out["merchant_category_encoded"] = (
            out["merchant_category"]
            .astype(str)
            .map(self.merchant_mapping_)
            .fillna(-1)
            .astype(int)
        )

        return out

    # ------------------------------------------------------------ accessors

    def get_feature_columns(self) -> list[str]:
        return list(self.feature_columns_)

    def get_X_y(
        self, df: pd.DataFrame
    ) -> tuple[pd.DataFrame, pd.Series]:
        X = df[self.feature_columns_].astype(np.float32)
        y = df["win_outcome"].astype(int)
        return X, y

    # ------------------------------------------------------------- pipeline

    def fit_transform(self, train_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        engineered = self.engineer_features(train_df, fit=True)

        self.scaler_ = StandardScaler()
        engineered[SCALED_NUMERIC_COLUMNS] = self.scaler_.fit_transform(
            engineered[SCALED_NUMERIC_COLUMNS]
        )

        self._fitted = True
        return self.get_X_y(engineered)

    def transform(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
        if not self._fitted:
            raise RuntimeError("Preprocessor not fitted. Call fit_transform() first.")
        engineered = self.engineer_features(df, fit=False)
        engineered[SCALED_NUMERIC_COLUMNS] = self.scaler_.transform(
            engineered[SCALED_NUMERIC_COLUMNS]
        )
        return self.get_X_y(engineered)

    # --------------------------------------------------------- persistence

    def save(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as fh:
            pickle.dump(self, fh)
        return path

    @classmethod
    def load(cls, path: str | Path) -> "ChargebackPreprocessor":
        with open(path, "rb") as fh:
            obj = pickle.load(fh)
        if not isinstance(obj, cls):
            raise TypeError(f"Artifact at {path} is not a ChargebackPreprocessor")
        return obj


def main() -> None:
    pre = ChargebackPreprocessor()
    csv_path = MODULE_DIR / "chargebacks_synthetic.csv"

    train, val, test = pre.load_data(csv_path)
    print(f"Loaded splits -> train={len(train):,}  val={len(val):,}  test={len(test):,}")

    X_train, y_train = pre.fit_transform(train)
    X_val, y_val = pre.transform(val)
    X_test, y_test = pre.transform(test)

    features = pre.get_feature_columns()
    print(f"\n--- FEATURE LIST ({len(features)} features) ---")
    for i, f in enumerate(features, 1):
        print(f"  {i:>2}. {f}")

    print("\n--- SHAPES ---")
    print(f"  X_train: {X_train.shape}   X_val: {X_val.shape}   X_test: {X_test.shape}")

    print("\n--- CLASS BALANCE ---")
    for name, y in [("train", y_train), ("val", y_val), ("test", y_test)]:
        rate = y.mean()
        print(f"  {name:>5}: win={int(y.sum()):,} ({rate:.1%})  lose={int((1 - y).sum()):,}")

    artifact_path = PACKAGE_DIR / "model" / "artifacts" / "preprocessor.pkl"
    pre.save(artifact_path)
    print(f"\nSaved preprocessor -> {artifact_path}")


if __name__ == "__main__":
    main()
