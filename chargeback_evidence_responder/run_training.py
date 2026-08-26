"""End-to-end training entry point.

Loads synthetic data -> preprocesses -> trains XGBoost (+ LR baseline) ->
optimises decision threshold -> evaluates on test -> saves artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_DIR))

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import numpy as np
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score

from data.generator import REASON_CODE_LABELS
from data.preprocessor import ChargebackPreprocessor
from model.trainer import ChargebackModelTrainer
from utils.logger import get_logger

logger = get_logger()

CSV_PATH = PACKAGE_DIR / "data" / "chargebacks_synthetic.csv"
PREPROCESSOR_PATH = PACKAGE_DIR / "model" / "artifacts" / "preprocessor.pkl"
MODEL_PATH = PACKAGE_DIR / "model" / "artifacts" / "model.pkl"


def main() -> int:
    pre = ChargebackPreprocessor()
    train_df, val_df, test_df = pre.load_data(CSV_PATH)
    logger.info("Data loaded: train={}, val={}, test={}",
                len(train_df), len(val_df), len(test_df))

    X_train, y_train = pre.fit_transform(train_df)
    X_val, y_val = pre.transform(val_df)
    X_test, y_test = pre.transform(test_df)
    pre.save(PREPROCESSOR_PATH)
    logger.info("Preprocessor fitted + saved ({} features)", len(pre.get_feature_columns()))

    trainer = ChargebackModelTrainer()
    trainer.train(X_train, y_train, X_val, y_val)
    analysis = trainer.find_optimal_threshold(X_val, y_val)
    trainer.save_model(MODEL_PATH)

    by_cost = analysis["by_cost"]
    by_f1 = analysis["by_f1"]

    print("\n" + "=" * 68)
    print("TRAINING COMPLETE — CHARGEBACK WIN-PROBABILITY MODEL")
    print("=" * 68)
    print(f"Features used          : {len(trainer.feature_names_)}")
    print(f"Best iteration         : {trainer.xgb_model.best_iteration}")
    auc_val = roc_auc_score(y_val, trainer.model_.predict_proba(X_val)[:, 1])
    auc_test = roc_auc_score(y_test, trainer.model_.predict_proba(X_test)[:, 1])
    print(f"ROC-AUC  val / test    : {auc_val:.4f} / {auc_test:.4f}")

    print("\n--- OPTIMAL THRESHOLDS (validation set) ---")
    print(f"  Cost-minimising : {by_cost['threshold']:.2f}   "
          f"P={by_cost['precision']:.3f}  R={by_cost['recall']:.3f}  F1={by_cost['f1']:.3f}  "
          f"cost ₹{by_cost['total_cost_inr']:,.0f}")
    print(f"  F1-maximising   : {by_f1['threshold']:.2f}   "
          f"P={by_f1['precision']:.3f}  R={by_f1['recall']:.3f}  F1={by_f1['f1']:.3f}  "
          f"cost ₹{by_f1['total_cost_inr']:,.0f}")

    thr = analysis["recommended_threshold"]
    probs_test = trainer.model_.predict_proba(X_test)[:, 1]
    preds_test = (probs_test >= thr).astype(int)
    p_t, r_t, f1_t, _ = precision_recall_fscore_support(
        y_test, preds_test, average="binary", zero_division=0
    )
    fp = int(np.sum((preds_test == 1) & (np.asarray(y_test) == 0)))
    fn = int(np.sum((preds_test == 0) & (np.asarray(y_test) == 1)))
    cost_cfg = trainer.config["costs"]
    total_cost_test = fp * (cost_cfg["chargeback_fee_inr"] + cost_cfg["response_effort_inr"]) \
        + fn * cost_cfg["avg_transaction_inr"] * 0.3

    print(f"\n--- TEST SET @ threshold {thr:.2f} ---")
    print(f"  Precision {p_t:.3f} | Recall {r_t:.3f} | F1 {f1_t:.3f} "
          f"| FP {fp:,} | FN {fn:,} | total cost ₹{total_cost_test:,.0f}")

    lr_auc = roc_auc_score(y_val, trainer.lr_model_.predict_proba(X_val)[:, 1])
    print(f"\nBaseline LogisticRegression val ROC-AUC: {lr_auc:.4f} "
          f"(XGBoost {auc_val:.4f})")

    print(f"\nArtifacts:\n  preprocessor -> {PREPROCESSOR_PATH}\n  model        -> {MODEL_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
