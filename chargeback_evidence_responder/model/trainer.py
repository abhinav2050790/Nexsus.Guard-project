"""XGBoost training pipeline with threshold optimisation.

Trains the win-probability classifier with early stopping, benchmarks a
LogisticRegression baseline, then searches the decision threshold that
minimises total business cost (chargeback fees + response effort vs. lost
principal) alongside the F1-maximising threshold.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from xgboost import XGBClassifier

from utils.logger import get_logger

logger = get_logger()

PACKAGE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PACKAGE_DIR / "config.yaml"

THRESHOLD_GRID = np.round(np.arange(0.10, 0.9001, 0.01), 2)


class ChargebackModelTrainer:
    """Train, tune and persist the XGBoost win-probability model."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        import yaml

        config_path = Path(config_path)
        if not config_path.is_absolute():
            candidate = PACKAGE_DIR / config_path
            config_path = candidate if candidate.exists() else config_path
        with open(config_path, "r", encoding="utf-8") as fh:
            self.config = yaml.safe_load(fh)

        params = self.config["model"]["params"]
        self.xgb_model = XGBClassifier(
            **params,
            tree_method="hist",
            eval_metric="logloss",
            early_stopping_rounds=50,
        )
        self.lr_model = LogisticRegression(max_iter=1000, random_state=params["random_state"])

        self.model_: XGBClassifier | None = None
        self.lr_model_: LogisticRegression | None = None
        self.threshold_analysis_: dict[str, Any] | None = None
        self.recommended_threshold_: float | None = None
        self.feature_names_: list[str] = []

    # -------------------------------------------------------------- training

    def train(
        self,
        X_train,
        y_train,
        X_val,
        y_val,
    ) -> XGBClassifier:
        self.feature_names_ = list(X_train.columns)

        logger.info("Training XGBoost on {} rows / {} features ...",
                    len(X_train), len(self.feature_names_))
        self.xgb_model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        self.model_ = self.xgb_model

        curve = self.xgb_model.evals_result()["validation_0"]["logloss"]
        best_iter = int(self.xgb_model.best_iteration)
        best_val_logloss = float(curve[best_iter])
        logger.info(
            "Loss curve: start={:.5f} -> best={:.5f} @ iter {} ({} rounds evaluated)",
            curve[0], best_val_logloss, best_iter, len(curve),
        )

        logger.info("Training LogisticRegression baseline ...")
        self.lr_model_ = self.lr_model.fit(X_train, y_train)

        p_xgb = self.xgb_model.predict_proba(X_val)[:, 1]
        p_lr = self.lr_model_.predict_proba(X_val)[:, 1]
        auc_xgb = roc_auc_score(y_val, p_xgb)
        auc_lr = roc_auc_score(y_val, p_lr)
        ll_xgb = log_loss(y_val, p_xgb)
        logger.info("Val ROC-AUC -> XGBoost: {:.4f} | LogisticRegression: {:.4f}", auc_xgb, auc_lr)
        logger.info("Val log-loss -> XGBoost: {:.4f}", ll_xgb)

        return self.model_

    # ---------------------------------------------------- threshold search

    def _metrics_at_threshold(
        self, y_true: np.ndarray, probs: np.ndarray, t: float, costs: dict[str, float]
    ) -> dict[str, float]:
        pred = (probs >= t).astype(int)
        tp = int(np.sum((pred == 1) & (y_true == 1)))
        fp = int(np.sum((pred == 1) & (y_true == 0)))
        fn = int(np.sum((pred == 0) & (y_true == 1)))

        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        )
        fp_cost = fp * (costs["chargeback_fee_inr"] + costs["response_effort_inr"])
        fn_cost = fn * costs["avg_transaction_inr"] * 0.3
        return {
            "threshold": float(t),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "false_positives": fp,
            "false_negatives": fn,
            "false_positive_cost_inr": float(fp_cost),
            "false_negative_cost_inr": float(fn_cost),
            "total_cost_inr": float(fp_cost + fn_cost),
        }

    def find_optimal_threshold(self, X_val, y_val) -> dict[str, Any]:
        if self.model_ is None:
            raise RuntimeError("Call train() before find_optimal_threshold().")

        y_true = np.asarray(y_val)
        probs = self.model_.predict_proba(X_val)[:, 1]
        costs = self.config["costs"]

        grid = [
            self._metrics_at_threshold(y_true, probs, t, costs) for t in THRESHOLD_GRID
        ]
        by_f1 = max(grid, key=lambda m: m["f1"])
        by_cost = min(grid, key=lambda m: m["total_cost_inr"])

        self.threshold_analysis_ = {
            "recommended_threshold": by_cost["threshold"],
            "by_cost": by_cost,
            "by_f1": {k: v for k, v in by_f1.items()},
        }
        self.recommended_threshold_ = by_cost["threshold"]

        logger.info(
            "Cost-optimal threshold: {:.2f} (P={:.3f} R={:.3f} F1={:.3f}, total cost ₹{:,.0f})",
            by_cost["threshold"], by_cost["precision"], by_cost["recall"],
            by_cost["f1"], by_cost["total_cost_inr"],
        )
        logger.info(
            "F1-optimal threshold:   {:.2f} (P={:.3f} R={:.3f} F1={:.3f}, total cost ₹{:,.0f})",
            by_f1["threshold"], by_f1["precision"], by_f1["recall"],
            by_f1["f1"], by_f1["total_cost_inr"],
        )
        return self.threshold_analysis_

    # ----------------------------------------------------------- persistence

    def save_model(self, path: str | Path) -> Path:
        if self.model_ is None or self.recommended_threshold_ is None:
            raise RuntimeError("Nothing to save — run train() and find_optimal_threshold() first.")
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "model": self.model_,
            "baseline_model": self.lr_model_,
            "best_threshold": self.recommended_threshold_,
            "threshold_analysis": self.threshold_analysis_,
            "feature_names": self.feature_names_,
            "metadata": {
                "trained_at": datetime.now().isoformat(timespec="seconds"),
                "n_samples_trained": int(self.model_.n_features_in_),
                "best_iteration": int(self.xgb_model.best_iteration),
                "xgb_params": {
                    k: (v if isinstance(v, (int, float, str, bool)) else str(v))
                    for k, v in self.config["model"]["params"].items()
                },
            },
        }
        joblib.dump(payload, path)
        logger.info("Model artifact saved -> {}", path)
        return path

    @classmethod
    def load_model(cls, path: str | Path) -> "ChargebackModelTrainer":
        path = Path(path)
        payload = joblib.load(path)
        trainer = cls()
        trainer.model_ = payload["model"]
        trainer.lr_model_ = payload.get("baseline_model")
        trainer.recommended_threshold_ = payload["best_threshold"]
        trainer.threshold_analysis_ = payload.get("threshold_analysis")
        trainer.feature_names_ = payload.get("feature_names", [])
        logger.info(
            "Model loaded from {} (trained {}, threshold {:.2f})",
            path,
            payload.get("metadata", {}).get("trained_at", "?"),
            payload["best_threshold"],
        )
        return trainer


if __name__ == "__main__":
    print(json.dumps({"module": "model.trainer", "status": "ready"}))
