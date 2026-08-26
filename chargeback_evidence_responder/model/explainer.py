"""SHAP-based explainability engine.

Translates XGBoost internals into merchant-friendly language: per-case
"why this score" narratives in plain English and global feature-importance
plots. Log-odds SHAP contributions are telescoped through the sigmoid so
each factor's impact reads as percentage points of win probability.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import sys
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap

from utils.logger import get_logger

logger = get_logger()

PLOTS_DIR = PACKAGE_DIR / "model" / "artifacts" / "plots"


def _sigmoid(x: float | np.ndarray) -> float | np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


FRIENDLY_PHRASES = {
    "is_3ds_verified": (
        "3-D Secure verification was completed",
        "the transaction was NOT verified with 3-D Secure",
    ),
    "avs_match": (
        "the billing address matched the bank's records",
        "the billing address did not match the bank's records",
    ),
    "cvv_match": (
        "the card security code matched",
        "the card security code did not match",
    ),
    "has_delivery_confirmation": (
        "delivery was confirmed by the courier",
        "there is no delivery confirmation on record",
    ),
    "has_signed_receipt": (
        "a signed proof of delivery exists",
        "there is no signed receipt for this order",
    ),
    "has_login_after_purchase": (
        "the customer logged into their account after the purchase",
        "the customer never logged in after the purchase",
    ),
    "has_support_interaction": (
        "the customer interacted with support (showing genuine engagement)",
        "the customer had no support interactions",
    ),
    "order_confirmation_sent": (
        "an order confirmation was sent to the customer",
        "no order confirmation was sent",
    ),
    "refund_policy_acknowledged": (
        "the customer acknowledged the refund policy",
        "the customer did not acknowledge the refund policy",
    ),
    "high_amount_flag": (
        "this is a high-value transaction worth fighting carefully",
        "this is a routine-value transaction",
    ),
    "chargeback_risk_flag": (
        "the customer has several prior chargebacks (unusual for a genuine customer)",
        None,
    ),
    "is_first_time_buyer": (
        None,
        "this is a brand-new customer with no purchase history",
    ),
    "is_high_value_customer": (
        "this is a loyal, high-value customer",
        None,
    ),
    "verification_score": (
        "overall payment verification was strong",
        "overall payment verification was weak",
    ),
    "customer_trust_score": (
        "the customer's trust history is strong",
        "the customer's trust history is weak",
    ),
    "evidence_completeness_score": (
        "nearly all possible evidence is on file for this order",
        "key evidence is missing from this order's record",
    ),
    "previous_chargebacks_count": (
        "the customer has few or no past chargebacks",
        "the customer has several past chargebacks",
    ),
    "previous_orders_count": (
        "the customer has a solid purchase history with you",
        "the customer has little purchase history with you",
    ),
    "customer_account_age_days": (
        "the customer's account is well established",
        "the customer's account is very new",
    ),
    "amount_risk_tier_encoded": (
        "the amount tier supports fighting this case",
        "the amount tier makes this case less attractive",
    ),
    "reason_code_encoded": (
        "this dispute category favours the merchant",
        "this dispute category is harder to win",
    ),
    "days_since_bucket_encoded": (
        "the dispute was raised soon after purchase",
        "the dispute came long after the purchase",
    ),
    "reason_code_historical_win_rate": (
        "merchants historically win this type of dispute often",
        "this dispute type is historically hard to win",
    ),
    "merchant_historical_win_rate": (
        "your store category wins similar disputes often",
        "your store category faces tougher odds on such disputes",
    ),
    "days_since_transaction": (
        "the transaction is recent, which helps evidence stay fresh",
        "the transaction is old, which weakens the case",
    ),
    "transaction_amount_inr": (
        "the amount profile supports fighting this case",
        "the amount profile makes this case less attractive to fight",
    ),
    "payment_method_risk": (
        "the payment method carries low dispute risk",
        "the payment method is associated with higher dispute risk",
    ),
}

GENERIC_FEATURE_LABEL = "factor '{}'".format


class ChargebackExplainer:
    """TreeExplainer wrapper producing human-readable case explanations."""

    def __init__(self, model, feature_names: list[str]) -> None:
        self.model = model
        self.feature_names = list(feature_names)
        self.explainer = shap.TreeExplainer(model)
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)
        self.importance_: dict[str, float] | None = None
        self._last_shap_: np.ndarray | None = None

    # ----------------------------------------------------------- single case

    def explain_single(self, x_row: pd.DataFrame) -> dict[str, Any]:
        if hasattr(x_row, "columns"):
            row = x_row.iloc[[0]] if len(x_row) > 1 else x_row.copy()
        else:
            row = pd.DataFrame([x_row], columns=self.feature_names)

        sv = np.asarray(self.explainer.shap_values(row))[0]
        base_value = float(np.ravel(self.explainer.expected_value)[0])

        win_prob = float(_sigmoid(base_value + sv.sum()))

        order = np.argsort(-np.abs(sv))
        pcts = self._telescope_to_pct(base_value, sv[order])

        positives, negatives = [], []
        for idx, pct in zip(order, pcts):
            feat = self.feature_names[idx]
            entry = {
                "feature": feat,
                "shap_value": round(float(sv[idx]), 4),
                "pct_points": round(float(pct), 1),
                "direction": "increases_win" if sv[idx] > 0 else "decreases_win",
            }
            if sv[idx] > 0 and len(positives) < 5:
                positives.append(entry)
            elif sv[idx] < 0 and len(negatives) < 5:
                negatives.append(entry)

        explanation_text = self._compose_narrative(row, positives, negatives, win_prob)

        return {
            "base_value": round(base_value, 4),
            "win_probability_pct": round(win_prob * 100, 1),
            "top_positive_factors": positives,
            "top_negative_factors": negatives,
            "explanation_text": explanation_text,
        }

    @staticmethod
    def _telescope_to_pct(base_value: float, sorted_shap: np.ndarray) -> list[float]:
        """Convert log-odds contributions to probability points that sum exactly."""
        running = base_value
        out = []
        for s in sorted_shap:
            before = _sigmoid(running)
            after = _sigmoid(running + s)
            out.append((after - before) * 100.0)
            running += s
        return out

    def _phrase_for(self, row: pd.DataFrame, feat: str, positive: bool) -> str:
        phrases = FRIENDLY_PHRASES.get(feat)
        phrase = (phrases[0] if positive else phrases[1]) if phrases else None
        if phrase is None:
            direction = "supports winning" if positive else "hurts the case"
            return f"{GENERIC_FEATURE_LABEL(feat)} {direction}"
        return phrase

    def _compose_narrative(
        self,
        row: pd.DataFrame,
        positives: list[dict[str, Any]],
        negatives: list[dict[str, Any]],
        win_prob: float,
    ) -> str:
        band = (
            "HIGH" if win_prob >= 0.60 else
            "MODERATE" if win_prob >= 0.30 else
            "LOW"
        )
        parts: list[str] = [
            f"This chargeback has a {band} chance of being won in your favour "
            f"(about {win_prob:.0%})."
        ]

        if positives:
            drivers = []
            for e in positives[:3]:
                phrase = self._phrase_for(row, e["feature"], positive=True)
                sign = "+" if e["pct_points"] >= 0 else ""
                drivers.append(f"{phrase} ({sign}{e['pct_points']:.0f} pts)")
            parts.append("Main strengths: " + "; ".join(drivers) + ".")

        if negatives:
            risks = []
            for e in negatives[:3]:
                phrase = self._phrase_for(row, e["feature"], positive=False)
                risks.append(f"{phrase} ({e['pct_points']:.0f} pts)")
            parts.append("Risk factors: " + "; ".join(risks) + ".")

        if not negatives:
            parts.append("No significant risk factors were detected for this case.")
        elif not positives:
            parts.append(
                "Consider gathering more proof before spending effort on this dispute."
            )

        return " ".join(parts)

    # ---------------------------------------------------------------- global

    def explain_global(self, X_test: pd.DataFrame, max_display: int = 15) -> dict[str, Path]:
        sample = X_test[self.feature_names]
        if len(sample) > 5000:
            sample = sample.iloc[:5000]

        sv = np.asarray(self.explainer.shap_values(sample))
        self._last_shap_ = sv

        mean_abs = np.abs(sv).mean(axis=0)
        self.importance_ = {
            f: round(float(v), 5)
            for f, v in sorted(
                zip(self.feature_names, mean_abs), key=lambda kv: -kv[1]
            )
        }
        top3 = list(self.importance_.keys())[:3]

        plt.figure()
        shap.summary_plot(sv, sample, plot_type="bar", max_display=max_display, show=False)
        bar_path = PLOTS_DIR / "shap_summary_bar.png"
        plt.tight_layout()
        plt.savefig(bar_path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved {}", bar_path)

        plt.figure()
        shap.summary_plot(sv, sample, max_display=max_display, show=False)
        dot_path = PLOTS_DIR / "shap_summary_dot.png"
        plt.tight_layout()
        plt.savefig(dot_path, dpi=150, bbox_inches="tight")
        plt.close()
        logger.info("Saved {}", dot_path)

        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        for ax, feat in zip(axes, top3):
            shap.dependence_plot(
                feat, sv, sample, ax=ax, show=False,
                interaction_index="auto",
            )
        dep_path = PLOTS_DIR / "shap_dependence_top3.png"
        fig.suptitle("SHAP Dependence — Top 3 Drivers", y=1.02)
        fig.tight_layout()
        fig.savefig(dep_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Saved {}", dep_path)

        return {
            "summary_bar": bar_path,
            "summary_dot": dot_path,
            "dependence_top3": dep_path,
        }

    def get_feature_importance(self) -> dict[str, float]:
        if self.importance_ is None:
            gain = self.model.feature_importances_
            self.importance_ = {
                f: round(float(v), 5)
                for f, v in sorted(
                    zip(self.feature_names, gain), key=lambda kv: -kv[1]
                )
            }
            logger.debug("Importance derived from model gain (run explain_global for SHAP-based).")
        return dict(self.importance_)


def main() -> int:
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    from data.preprocessor import ChargebackPreprocessor
    from model.trainer import ChargebackModelTrainer

    pre = ChargebackPreprocessor.load(PACKAGE_DIR / "model" / "artifacts" / "preprocessor.pkl")
    trainer = ChargebackModelTrainer.load_model(PACKAGE_DIR / "model" / "artifacts" / "model.pkl")

    _, _, test_df = pre.load_data(PACKAGE_DIR / "data" / "chargebacks_synthetic.csv")
    X_test, _ = pre.transform(test_df)

    ex = ChargebackExplainer(trainer.model_, trainer.feature_names_)
    ex.explain_global(X_test)

    importance = ex.get_feature_importance()
    print("\n" + "=" * 68)
    print("GLOBAL FEATURE IMPORTANCE (mean |SHAP|)")
    print("=" * 68)
    for rank, (feat, score) in enumerate(importance.items(), 1):
        bar = "#" * max(1, int(score / max(importance.values()) * 40))
        print(f"{rank:>2}. {feat:<38} {score:>8.4f}  {bar}")

    print("\n--- SINGLE-CASE EXPLANATION DEMO ---")
    probs = trainer.model_.predict_proba(X_test)[:, 1]
    strong_idx = int(np.argmax(probs))
    weak_idx = int(np.argmin(probs))

    for label, idx in [("STRONGEST case", strong_idx), ("WEAKEST case", weak_idx)]:
        result = ex.explain_single(X_test.iloc[[idx]])
        print(f"\n[{label}] p(win)={result['win_probability_pct']}%")
        print(result["explanation_text"])
        print("Top factors:")
        for e in result["top_positive_factors"][:3]:
            print(f"  + {e['feature']:<35} {e['shap_value']:+.3f}")
        for e in result["top_negative_factors"][:3]:
            print(f"  - {e['feature']:<35} {e['shap_value']:+.3f}")

    print(f"\nAll explanation plots saved to: {PLOTS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
