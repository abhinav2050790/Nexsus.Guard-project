"""Cached evaluation payload builder for the Streamlit dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np


def evaluate_everything(package_dir: Path) -> dict[str, Any]:
    from data.preprocessor import ChargebackPreprocessor
    from model.evaluator import ChargebackEvaluator
    from model.trainer import ChargebackModelTrainer

    pkg = Path(package_dir)
    pre = ChargebackPreprocessor.load(pkg / "model" / "artifacts" / "preprocessor.pkl")
    trainer = ChargebackModelTrainer.load_model(pkg / "model" / "artifacts" / "model.pkl")
    evaluator = ChargebackEvaluator()

    _, _, test_df = pre.load_data(pkg / "data" / "chargebacks_synthetic.csv")
    X_test, y_test = pre.transform(test_df)
    threshold = float(trainer.recommended_threshold_ or 0.76)

    metrics = evaluator.evaluate(trainer.model_, X_test, y_test, threshold, evaluator.config)

    probs = trainer.model_.predict_proba(X_test)[:, 1]
    y_true = np.asarray(y_test).astype(int)

    from sklearn.metrics import precision_recall_curve, roc_curve

    fpr, tpr, _ = roc_curve(y_true, probs)
    precision_curve, recall_curve, _ = precision_recall_curve(y_true, probs)

    costs_cfg = evaluator.config["costs"]
    thresholds = np.round(np.arange(0.10, 0.9001, 0.01), 2)
    total_costs = []
    for t in thresholds:
        pred = (probs >= t).astype(int)
        fp = int(np.sum((pred == 1) & (y_true == 0)))
        fn = int(np.sum((pred == 0) & (y_true == 1)))
        total_costs.append(
            fp * (costs_cfg["chargeback_fee_inr"] + costs_cfg["response_effort_inr"])
            + fn * costs_cfg["avg_transaction_inr"] * 0.3
        )

    from model.explainer import ChargebackExplainer

    explainer = ChargebackExplainer(trainer.model_, trainer.feature_names_)
    sample = X_test.iloc[:1000]
    sv = np.asarray(explainer.explainer.shap_values(sample))
    mean_abs = np.abs(sv).mean(axis=0)
    importance = {
        f: round(float(v), 5)
        for f, v in sorted(zip(trainer.feature_names_, mean_abs), key=lambda kv: -kv[1])
    }

    return {
        "metrics": metrics,
        "fpr": fpr.tolist(),
        "tpr": tpr.tolist(),
        "precision_curve": precision_curve.tolist(),
        "recall_curve": recall_curve.tolist(),
        "thresholds": thresholds.tolist(),
        "total_costs": [float(c) for c in total_costs],
        "best_threshold": float(thresholds[int(np.argmin(total_costs))]),
        "importance": importance,
    }
