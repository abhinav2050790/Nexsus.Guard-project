"""Synthetic chargeback dataset generator.

Produces 50,000 realistic chargeback records spanning transaction, customer,
verification, evidence-availability and historical features. The win_outcome
target is Bernoulli-sampled from a transparent probability model driven by
verification strength, evidence availability and cardholder risk history.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

MODULE_DIR = Path(__file__).resolve().parent
PACKAGE_DIR = MODULE_DIR.parent
CONFIG_PATH = PACKAGE_DIR / "config.yaml"
OUTPUT_PATH = MODULE_DIR / "chargebacks_synthetic.csv"

PAYMENT_METHODS = ["card_credit", "card_debit", "upi", "netbanking", "wallet"]
PAYMENT_WEIGHTS = [0.35, 0.25, 0.20, 0.15, 0.05]

MERCHANT_CATEGORIES = [
    "electronics",
    "fashion",
    "travel",
    "food",
    "grocery",
    "education",
    "healthcare",
    "gaming",
    "subscription",
    "other",
]
MERCHANT_CATEGORY_WIN_RATES: dict[str, float] = {
    "electronics": 0.62,
    "fashion": 0.48,
    "travel": 0.55,
    "food": 0.70,
    "grocery": 0.78,
    "education": 0.65,
    "healthcare": 0.58,
    "gaming": 0.35,
    "subscription": 0.45,
    "other": 0.52,
}

REASON_CODES = ["CB001", "CB002", "CB003", "CB004"]
REASON_CODE_WEIGHTS = [0.45, 0.25, 0.15, 0.15]
DEFAULT_REASON_CODE_WIN_RATES: dict[str, float] = {
    "CB001": 0.72,
    "CB002": 0.58,
    "CB003": 0.45,
    "CB004": 0.81,
}
REASON_CODE_LABELS = {
    "CB001": "unauthorized",
    "CB002": "non_receipt",
    "CB003": "not_as_described",
    "CB004": "friendly_fraud",
}

EVIDENCE_ORDER = [
    "is_3ds_verified",
    "has_delivery_confirmation",
    "avs_match",
    "cvv_match",
    "has_signed_receipt",
    "has_login_after_purchase",
    "has_support_interaction",
    "order_confirmation_sent",
    "refund_policy_acknowledged",
]

AMOUNT_SIGMA = 0.8
AMOUNT_MIN_INR = 500.0
AMOUNT_MAX_INR = 150000.0


def load_config(path: Path = CONFIG_PATH) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _lognormal_amounts(rng: np.random.Generator, n: int) -> np.ndarray:
    target_mean = 8500.0
    mu = np.log(target_mean) - 0.5 * AMOUNT_SIGMA**2
    amounts = rng.lognormal(mean=mu, sigma=AMOUNT_SIGMA, size=n)
    return np.clip(np.round(amounts, 2), AMOUNT_MIN_INR, AMOUNT_MAX_INR)


def _random_dates(rng: np.random.Generator, n: int) -> list[str]:
    today = date.today()
    offsets = rng.integers(0, 365, size=n)
    return [(today - timedelta(days=int(off))).isoformat() for off in offsets]


def _win_probability(
    reason_codes: np.ndarray,
    rc_win_rates: dict[str, float],
    is_3ds: np.ndarray,
    has_delivery: np.ndarray,
    avs: np.ndarray,
    cvv: np.ndarray,
    signed: np.ndarray,
    login_after: np.ndarray,
    support: np.ndarray,
    prev_chargebacks: np.ndarray,
    days_since: np.ndarray,
    account_age: np.ndarray,
) -> np.ndarray:
    base = np.array([rc_win_rates[rc] for rc in reason_codes], dtype=float)

    prob = base.copy()
    prob += 0.20 * is_3ds
    prob += 0.15 * has_delivery
    prob += 0.10 * avs
    prob += 0.08 * cvv
    prob += 0.12 * signed
    prob += 0.07 * login_after
    prob += 0.05 * support

    chargeback_penalty = np.minimum(0.05 * prev_chargebacks.astype(float), 0.20)
    prob -= chargeback_penalty
    prob -= 0.10 * (days_since > 90).astype(float)
    prob -= 0.15 * (account_age < 30).astype(float)

    return np.clip(prob, 0.05, 0.95)


def generate_dataset(
    n_samples: int | None = None,
    seed: int | None = None,
    config_path: Path = CONFIG_PATH,
) -> pd.DataFrame:
    cfg = load_config(config_path)
    data_cfg = cfg["data"]
    n = n_samples if n_samples is not None else int(data_cfg["n_samples"])
    seed = seed if seed is not None else int(data_cfg["random_state"])
    rng = np.random.default_rng(seed)

    evidence_weights_map = cfg["evidence_weights"]
    weights_vec = np.array(
        [float(evidence_weights_map[name]) for name in EVIDENCE_ORDER], dtype=float
    )

    rc_win_rates = {
        code: float(cfg.get("reason_codes", {}).get(code, {}).get("historical_win_rate",
                 DEFAULT_REASON_CODE_WIN_RATES[code]))
        for code in REASON_CODES
    }

    transaction_id = [str(uuid.uuid4()) for _ in range(n)]
    transaction_date = _random_dates(rng, n)
    transaction_amount_inr = _lognormal_amounts(rng, n)
    payment_method = rng.choice(PAYMENT_METHODS, size=n, p=PAYMENT_WEIGHTS)
    merchant_category = rng.choice(MERCHANT_CATEGORIES, size=n)
    chargeback_reason_code = rng.choice(REASON_CODES, size=n, p=REASON_CODE_WEIGHTS)
    days_since_transaction = rng.integers(1, 181, size=n)

    customer_id = np.array(
        [f"CUST{num:06d}" for num in rng.choice(999999, size=n, replace=False)],
        dtype=object,
    )
    customer_account_age_days = rng.integers(0, 2001, size=n)
    previous_orders_count = rng.integers(0, 201, size=n)
    previous_chargebacks_count = rng.integers(0, 11, size=n)
    is_high_value_customer = previous_orders_count > 20

    u = lambda p: (rng.random(n) < p).astype(bool)  # noqa: E731
    is_3ds_verified = u(0.70)
    avs_match = u(0.65)
    cvv_match = u(0.80)
    has_delivery_confirmation = u(0.60)
    has_signed_receipt = has_delivery_confirmation & u(0.40)
    has_login_after_purchase = u(0.55)
    has_support_interaction = u(0.30)
    order_confirmation_sent = u(0.85)
    refund_policy_acknowledged = u(0.75)

    evidence_matrix = np.column_stack(
        [
            is_3ds_verified,
            has_delivery_confirmation,
            avs_match,
            cvv_match,
            has_signed_receipt,
            has_login_after_purchase,
            has_support_interaction,
            order_confirmation_sent,
            refund_policy_acknowledged,
        ]
    ).astype(float)
    evidence_completeness_score = np.round(evidence_matrix @ weights_vec, 3)

    merchant_historical_win_rate = np.array(
        [MERCHANT_CATEGORY_WIN_RATES[cat] for cat in merchant_category], dtype=float
    )
    reason_code_historical_win_rate = np.array(
        [rc_win_rates[rc] for rc in chargeback_reason_code], dtype=float
    )

    final_prob = _win_probability(
        chargeback_reason_code,
        rc_win_rates,
        is_3ds_verified,
        has_delivery_confirmation,
        avs_match,
        cvv_match,
        has_signed_receipt,
        has_login_after_purchase,
        has_support_interaction,
        previous_chargebacks_count,
        days_since_transaction,
        customer_account_age_days,
    )
    win_outcome = rng.binomial(1, final_prob)

    split = _stratified_split(win_outcome, data_cfg, rng)

    df = pd.DataFrame(
        {
            "transaction_id": transaction_id,
            "transaction_date": transaction_date,
            "transaction_amount_inr": transaction_amount_inr,
            "payment_method": payment_method,
            "merchant_category": merchant_category,
            "chargeback_reason_code": chargeback_reason_code,
            "days_since_transaction": days_since_transaction,
            "customer_id": customer_id,
            "customer_account_age_days": customer_account_age_days,
            "previous_orders_count": previous_orders_count,
            "previous_chargebacks_count": previous_chargebacks_count,
            "is_high_value_customer": is_high_value_customer,
            "is_3ds_verified": is_3ds_verified,
            "avs_match": avs_match,
            "cvv_match": cvv_match,
            "has_delivery_confirmation": has_delivery_confirmation,
            "has_signed_receipt": has_signed_receipt,
            "has_login_after_purchase": has_login_after_purchase,
            "has_support_interaction": has_support_interaction,
            "order_confirmation_sent": order_confirmation_sent,
            "refund_policy_acknowledged": refund_policy_acknowledged,
            "evidence_completeness_score": evidence_completeness_score,
            "merchant_historical_win_rate": merchant_historical_win_rate,
            "reason_code_historical_win_rate": reason_code_historical_win_rate,
            "win_outcome": win_outcome,
            "split": split,
        }
    )
    return df


def _stratified_split(
    win_outcome: np.ndarray, data_cfg: dict[str, Any], rng: np.random.Generator
) -> np.ndarray:
    val_size = float(data_cfg["val_size"])
    test_size = float(data_cfg["test_size"])
    state = int(data_cfg["random_state"])

    idx = np.arange(len(win_outcome))
    train_idx, hold_idx = train_test_split(
        idx, test_size=(test_size + val_size), stratify=win_outcome, random_state=state
    )
    rel_test = test_size / (test_size + val_size)
    val_idx, test_idx = train_test_split(
        hold_idx,
        test_size=rel_test,
        stratify=win_outcome[hold_idx],
        random_state=state,
    )

    split = np.empty(len(win_outcome), dtype=object)
    split[train_idx] = "train"
    split[val_idx] = "val"
    split[test_idx] = "test"
    return split


def print_summary(df: pd.DataFrame) -> None:
    total = len(df)
    wins = int(df["win_outcome"].sum())

    print("=" * 68)
    print("SYNTHETIC CHARGEBACK DATASET — GENERATION SUMMARY")
    print("=" * 68)
    print(f"\nShape: {df.shape[0]:,} rows x {df.shape[1]} columns")

    print("\n--- CLASS BALANCE (win_outcome) ---")
    for outcome, cnt in df["win_outcome"].value_counts().sort_index().items():
        label = "WON" if outcome == 1 else "LOST"
        print(f"  {label}: {cnt:,} ({cnt / total:.1%})")
    print(f"  Overall win rate: {wins / total:.1%}")

    print("\n--- WIN RATE BY REASON CODE ---")
    grp = df.groupby("chargeback_reason_code")["win_outcome"].agg(["count", "mean"])
    for code, row in grp.iterrows():
        label = REASON_CODE_LABELS.get(code, "?")
        print(f"  {code} ({label:<17}): n={int(row['count']):>6,}  win={row['mean']:.1%}")

    print("\n--- SPLIT DISTRIBUTION ---")
    for name, cnt in df["split"].value_counts().items():
        rate = df.loc[df["split"] == name, "win_outcome"].mean()
        print(f"  {name:>5}: {cnt:>6,} rows ({cnt / total:.0%}) | win rate {rate:.1%}")

    print("\n--- EVIDENCE COMPLETENESS DISTRIBUTION (0-1) ---")
    desc = df["evidence_completeness_score"].describe()
    for stat in ["mean", "std", "min", "25%", "50%", "75%", "max"]:
        print(f"  {stat:>5}: {desc[stat]:.3f}")
    bins = pd.cut(df["evidence_completeness_score"], bins=[0, .2, .4, .6, .8, 1.001],
                  include_lowest=True)
    for interval, cnt in bins.value_counts().sort_index().items():
        bar = "#" * max(1, int(cnt / total * 50))
        print(f"  {str(interval):<14}: {cnt:>6,} {bar}")

    print("\n--- SAMPLE ROWS (first 5) ---")
    with pd.option_context("display.max_columns", None, "display.width", 220):
        print(df.head(5).to_string(index=False))


def main() -> None:
    df = generate_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print_summary(df)
    print(f"\nSaved dataset -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
