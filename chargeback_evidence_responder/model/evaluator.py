"""Comprehensive evaluation with honest business-cost reporting.

Combines standard ML metrics (accuracy, precision/recall/F1, ROC-AUC,
PR-AUC, confusion matrix) with rupee-denominated business impact metrics
(false-positive fighting costs vs. recovered transaction value and ROI),
plus per-reason-code breakdowns and publication-ready plots.
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
import yaml
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from data.preprocessor import REASON_CODE_ENCODED
from utils.logger import get_logger

logger = get_logger()

DEFAULT_CONFIG_PATH = PACKAGE_DIR / "config.yaml"
PLOTS_DIR = PACKAGE_DIR / "model" / "artifacts" / "plots"
REPORT_PATH = PACKAGE_DIR / "model" / "artifacts" / "evaluation_report.txt"

ENCODED_TO_REASON = {v: k for k, v in REASON_CODE_ENCODED.items()}


class ChargebackEvaluator:
    """Model + cost evaluator producing metrics dicts, plots and reports."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        with open(config_path, "r", encoding="utf-8") as fh:
            self.config = yaml.safe_load(fh)
        PLOTS_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------ core eval

    def evaluate(
        self,
        model,
        X_test: pd.DataFrame,
        y_test,
        threshold: float,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        cfg = config or self.config
        costs = cfg["costs"]

        y_true = np.asarray(y_test).astype(int)
        probs = model.predict_proba(X_test)[:, 1]
        y_pred = (probs >= threshold).astype(int)

        cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        fp_per_case = float(costs["chargeback_fee_inr"] + costs["response_effort_inr"])
        total_fp_cost = fp * fp_per_case
        total_fn_cost = fn * costs["avg_transaction_inr"] * 0.3
        net_value_recovered = tp * costs["avg_transaction_inr"] * 0.8
        roi_percent = (
            (net_value_recovered - total_fp_cost) / total_fp_cost * 100
            if total_fp_cost > 0
            else 0.0
        )

        reason_codes_series = X_test["reason_code_encoded"].map(ENCODED_TO_REASON)
        per_reason: dict[str, dict[str, Any]] = {}
        for code in ["CB001", "CB002", "CB003", "CB004"]:
            mask = (reason_codes_series == code).to_numpy()
            n = int(mask.sum())
            if n == 0:
                per_reason[code] = {
                    "precision": 0.0, "recall": 0.0, "f1": 0.0,
                    "win_rate": 0.0, "count": 0,
                }
                continue
            yt, yp = y_true[mask], y_pred[mask]
            per_reason[code] = {
                "precision": round(float(precision_score(yt, yp, zero_division=0)), 4),
                "recall": round(float(recall_score(yt, yp, zero_division=0)), 4),
                "f1": round(float(f1_score(yt, yp, zero_division=0)), 4),
                "win_rate": round(float(yt.mean()), 4),
                "count": n,
            }

        metrics: dict[str, Any] = {
            "threshold": float(threshold),
            "accuracy": round(float((y_true == y_pred).mean()), 4),
            "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
            "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "roc_auc_score": round(float(roc_auc_score(y_true, probs)), 4),
            "average_precision_score": round(float(average_precision_score(y_true, probs)), 4),
            "confusion_matrix": {"TP": tp, "TN": tn, "FP": fp, "FN": fn},
            "false_positive_count": fp,
            "false_negative_count": fn,
            "false_positive_cost_per_case_inr": fp_per_case,
            "total_false_positive_cost_inr": float(total_fp_cost),
            "total_false_negative_cost_inr": float(total_fn_cost),
            "net_value_recovered_inr": float(net_value_recovered),
            "roi_percent": round(float(roi_percent), 2),
            "per_reason_code": per_reason,
            "n_samples": int(len(y_true)),
            "base_win_rate": round(float(y_true.mean()), 4),
        }
        return metrics

    # ---------------------------------------------------------------- plots

    def plot_roc_curve(self, model, X_test, y_test) -> Path:
        y_true = np.asarray(y_test).astype(int)
        probs = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_true, probs)
        auc = roc_auc_score(y_true, probs)

        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(fpr, tpr, lw=2, label=f"XGBoost (AUC = {auc:.4f})")
        ax.plot([0, 1], [0, 1], "--", color="grey", lw=1, label="Random (AUC = 0.5)")
        ax.set_xlabel("False Positive Rate")
        ax.set_ylabel("True Positive Rate")
        ax.set_title("ROC Curve — Chargeback Win Probability")
        ax.legend(loc="lower right")
        ax.grid(alpha=0.3)
        out = PLOTS_DIR / "roc_curve.png"
        fig.tight_layout()
        fig.savefig(out, dpi=150)
        plt.close(fig)
        logger.info("Saved {}", out)
        return out

    def plot_precision_recall_curve(self, model, X_test, y_test) -> Path:
        y_true = np.asarray(y_test).astype(int)
        probs = model.predict_proba(X_test)[:, 1]
        prec, rec, _ = precision_recall_curve(y_true, probs)
        ap = average_precision_score(y_true, probs)

        fig, ax = plt.subplots(figsize=(7, 6))
        ax.plot(rec, prec, lw=2, label=f"XGBoost (AP = {ap:.4f})")
        ax.axhline(np.asarray(y_true).mean(), ls="--", color="grey", lw=1,
                   label=f"Baseline ({np.asarray(y_true).mean():.2%})")
        ax.set_xlabel("Recall")
        ax.set_ylabel("Precision")
        ax.set_title("Precision-Recall Curve — Chargeback Win Probability")
        ax.legend(loc="upper right")
        ax.grid(alpha=0.3)
        out = PLOTS_DIR / "pr_curve.png"
        fig.tight_layout()
        fig.savefig(out, dpi=150)
        plt.close(fig)
        logger.info("Saved {}", out)
        return out

    def plot_cost_vs_threshold(self, model, X_test, y_test, config=None) -> Path:
        cfg = config or self.config
        costs = cfg["costs"]
        y_true = np.asarray(y_test).astype(int)
        probs = model.predict_proba(X_test)[:, 1]

        thresholds = np.round(np.arange(0.10, 0.9001, 0.01), 2)
        totals, fps, fns = [], [], []
        for t in thresholds:
            pred = (probs >= t).astype(int)
            fp = int(np.sum((pred == 1) & (y_true == 0)))
            fn = int(np.sum((pred == 0) & (y_true == 1)))
            fps.append(fp)
            fns.append(fn)
            totals.append(fp * (costs["chargeback_fee_inr"] + costs["response_effort_inr"])
                          + fn * costs["avg_transaction_inr"] * 0.3)

        best_i = int(np.argmin(totals))

        fig, ax = plt.subplots(figsize=(9, 6))
        ax.plot(thresholds, np.array(totals) / 1e6, lw=2, label="Total cost (INR millions)")
        ax.plot(thresholds, np.array(fps) / 1000, "--", lw=1.2, alpha=0.8,
                label="False positives (thousands of cases)")
        ax.plot(thresholds, np.array(fns) / 1000, ":", lw=1.2, alpha=0.8,
                label="False negatives (thousands of cases)")
        ax.axvline(thresholds[best_i], color="red", lw=1, ls="--",
                   label=f"Cost-min threshold = {thresholds[best_i]:.2f}")
        ax.set_xlabel("Decision Threshold (win probability cut-off)")
        ax.set_ylabel("Cost / Count")
        ax.set_title("Business Cost vs Threshold — Test Set")
        ax.legend()
        ax.grid(alpha=0.3)
        out = PLOTS_DIR / "cost_curve.png"
        fig.tight_layout()
        fig.savefig(out, dpi=150)
        plt.close(fig)
        logger.info("Saved {} (min cost Rs {:,.0f} @ {:.2f})",
                    out, totals[best_i], thresholds[best_i])
        return out

    def plot_confusion_matrix(self, y_test, y_pred) -> Path:
        y_true = np.asarray(y_test).astype(int)
        y_hat = np.asarray(y_pred).astype(int)
        cm = confusion_matrix(y_true, y_hat, labels=[0, 1])

        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(cm, cmap="Blues")
        labels = [["TN", "FP"], ["FN", "TP"]]
        for i in range(2):
            for j in range(2):
                ax.text(j, i, f"{labels[i][j]}\n{cm[i, j]:,}", ha="center", va="center",
                        fontsize=13, fontweight="bold",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        ax.set_xticks([0, 1], ["Predicted LOSE", "Predicted WIN"])
        ax.set_yticks([0, 1], ["Actual LOSE", "Actual WIN"])
        ax.set_title("Confusion Matrix — Test Set")
        fig.colorbar(im, shrink=0.85)
        out = PLOTS_DIR / "confusion_matrix.png"
        fig.tight_layout()
        fig.savefig(out, dpi=150)
        plt.close(fig)
        logger.info("Saved {}", out)
        return out

    # --------------------------------------------------------------- report

    def generate_evaluation_report(self, m: dict[str, Any], path: Path = REPORT_PATH) -> Path:
        cm = m["confusion_matrix"]
        lines = [
            "=" * 70,
            "CHARGEBACK EVIDENCE RESPONDER - MODEL EVALUATION REPORT",
            "=" * 70,
            "",
            f"Samples evaluated      : {m['n_samples']:,}",
            f"Decision threshold     : {m['threshold']:.2f}",
            f"Base win rate          : {m['base_win_rate']:.1%}",
            "",
            "--- STANDARD ML METRICS ---",
            f"Accuracy               : {m['accuracy']:.4f}",
            f"Precision              : {m['precision']:.4f}",
            f"Recall                 : {m['recall']:.4f}",
            f"F1 Score               : {m['f1_score']:.4f}",
            f"ROC-AUC                : {m['roc_auc_score']:.4f}",
            f"Average Precision (PR) : {m['average_precision_score']:.4f}",
            "",
            "--- CONFUSION MATRIX ---",
            f"TP {cm['TP']:>7,}   FP {cm['FP']:>7,}",
            f"FN {cm['FN']:>7,}   TN {cm['TN']:>7,}",
            "",
            "--- BUSINESS COST METRICS (INR) ---",
            f"Fought-but-lost (FP)   : {m['false_positive_count']:,} cases",
            f"Skipped-but-winnable(FN): {m['false_negative_count']:,} cases",
            f"FP cost per case       : INR {m['false_positive_cost_per_case_inr']:,.0f}",
            f"Total FP cost          : INR {m['total_false_positive_cost_inr']:,.0f}",
            f"Total FN cost          : INR {m['total_false_negative_cost_inr']:,.0f}",
            f"Net value recovered    : INR {m['net_value_recovered_inr']:,.0f}",
            f"ROI percent            : {m['roi_percent']:.2f}%",
            "",
            "--- PER REASON CODE ---",
            f"{'Code':<6} {'Count':>7} {'WinRate':>8} {'Prec':>7} {'Rec':>7} {'F1':>7}",
        ]
        for code, r in m["per_reason_code"].items():
            lines.append(
                f"{code:<6} {r['count']:>7,} {r['win_rate']:>8.1%} "
                f"{r['precision']:>7.3f} {r['recall']:>7.3f} {r['f1']:>7.3f}"
            )
        lines += ["", "=" * 70, ""]

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Saved {}", path)
        return path


def main() -> int:
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    from data.preprocessor import ChargebackPreprocessor
    from model.trainer import ChargebackModelTrainer

    PACKAGE = Path(__file__).resolve().parent.parent
    pre = ChargebackPreprocessor.load(PACKAGE / "model" / "artifacts" / "preprocessor.pkl")
    trainer = ChargebackModelTrainer.load_model(PACKAGE / "model" / "artifacts" / "model.pkl")

    _, _, test_df = pre.load_data(PACKAGE / "data" / "chargebacks_synthetic.csv")
    X_test, y_test = pre.transform(test_df)

    ev = ChargebackEvaluator()
    metrics = ev.evaluate(
        trainer.model_, X_test, y_test,
        threshold=trainer.recommended_threshold_, config=ev.config,
    )

    ev.plot_roc_curve(trainer.model_, X_test, y_test)
    ev.plot_precision_recall_curve(trainer.model_, X_test, y_test)
    ev.plot_cost_vs_threshold(trainer.model_, X_test, y_test)
    y_pred = (trainer.model_.predict_proba(X_test)[:, 1] >= trainer.recommended_threshold_).astype(int)
    ev.plot_confusion_matrix(y_test, y_pred)
    ev.generate_evaluation_report(metrics)

    print("\n" + "=" * 68)
    print("FULL EVALUATION — TEST SET")
    print("=" * 68)
    print(f"Samples                : {metrics['n_samples']:,}")
    print(f"Threshold              : {metrics['threshold']:.2f}")
    print(f"Precision              : {metrics['precision']:.4f}")
    print(f"Recall                 : {metrics['recall']:.4f}")
    print(f"F1 Score               : {metrics['f1_score']:.4f}")
    print(f"ROC-AUC                : {metrics['roc_auc_score']:.4f}")
    print(f"Avg Precision (PR-AUC) : {metrics['average_precision_score']:.4f}")
    print(f"Confusion matrix       : {metrics['confusion_matrix']}")
    print(f"Total FP cost          : INR {metrics['total_false_positive_cost_inr']:,.0f}")
    print(f"Net value recovered    : INR {metrics['net_value_recovered_inr']:,.0f}")
    print(f"ROI                    : {metrics['roi_percent']:.2f}%")
    print("\nPer reason code:")
    for code, r in metrics["per_reason_code"].items():
        print(f"  {code}: n={r['count']:>6,} win={r['win_rate']:.1%} "
              f"P={r['precision']:.3f} R={r['recall']:.3f} F1={r['f1']:.3f}")
    print("\nPlots + report saved to model/artifacts/plots/ and evaluation_report.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
