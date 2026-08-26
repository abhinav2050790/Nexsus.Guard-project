"""End-to-end pipeline runner.

Generates the dataset, preprocesses, trains (only if no model artifact exists),
evaluates with plots and report, produces SHAP explanations, pushes one sample
chargeback through the full production pipeline, and prints a launch summary.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PACKAGE_DIR))

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def banner(title: str) -> None:
    print(f"\n{'=' * 68}\n  {title}\n{'=' * 68}")


def main() -> int:
    t0 = datetime.now()

    csv_path = PACKAGE_DIR / "data" / "chargebacks_synthetic.csv"
    pre_pkl = PACKAGE_DIR / "model" / "artifacts" / "preprocessor.pkl"
    model_pkl = PACKAGE_DIR / "model" / "artifacts" / "model.pkl"

    # ---------------------------------------------------------- 1. generate
    banner("STEP 1/6 — SYNTHETIC DATASET")
    from data.generator import generate_dataset, print_summary

    df = generate_dataset()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print_summary(df)

    # ------------------------------------------------------ 2. preprocess
    banner("STEP 2/6 — FEATURE ENGINEERING")
    from data.preprocessor import ChargebackPreprocessor

    pre = ChargebackPreprocessor()
    train_df, val_df, test_df = pre.load_data(csv_path)
    X_train, y_train = pre.fit_transform(train_df)
    X_val, y_val = pre.transform(val_df)
    X_test, y_test = pre.transform(test_df)
    pre.save(pre_pkl)
    print(f"Features: {len(pre.get_feature_columns())}")
    print(f"Shapes: train={X_train.shape} val={X_val.shape} test={X_test.shape}")

    # ----------------------------------------------------------- 3. train
    banner("STEP 3/6 — MODEL TRAINING")
    from model.trainer import ChargebackModelTrainer

    if model_pkl.exists():
        trainer = ChargebackModelTrainer.load_model(model_pkl)
        print(f"Existing artifact reused (threshold {trainer.recommended_threshold_}).")
        print("Delete model/artifacts/model.pkl to force retraining.")
    else:
        trainer = ChargebackModelTrainer()
        trainer.train(X_train, y_train, X_val, y_val)
        analysis = trainer.find_optimal_threshold(X_val, y_val)
        trainer.save_model(model_pkl)
        print(f"Best iteration : {trainer.xgb_model.best_iteration}")
        print(f"Threshold      : {analysis['recommended_threshold']}")

    threshold = float(trainer.recommended_threshold_ or 0.76)

    # -------------------------------------------------------- 4. evaluate
    banner("STEP 4/6 — EVALUATION + COST ANALYSIS")
    from model.evaluator import ChargebackEvaluator

    ev = ChargebackEvaluator()
    metrics = ev.evaluate(trainer.model_, X_test, y_test, threshold, ev.config)
    ev.plot_roc_curve(trainer.model_, X_test, y_test)
    ev.plot_precision_recall_curve(trainer.model_, X_test, y_test)
    ev.plot_cost_vs_threshold(trainer.model_, X_test, y_test)
    y_pred = (trainer.model_.predict_proba(X_test)[:, 1] >= threshold).astype(int)
    ev.plot_confusion_matrix(y_test, y_pred)
    ev.generate_evaluation_report(metrics)

    cm = metrics["confusion_matrix"]
    print(f"P={metrics['precision']:.3f}  R={metrics['recall']:.3f}  "
          f"F1={metrics['f1_score']:.3f}  ROC-AUC={metrics['roc_auc_score']:.4f}")
    print(f"TP {cm['TP']:,} | TN {cm['TN']:,} | FP {cm['FP']:,} | FN {cm['FN']:,}")
    print(f"FP cost ₹{metrics['total_false_positive_cost_inr']:,.0f} | "
          f"net recovered ₹{metrics['net_value_recovered_inr']:,.0f} | "
          f"ROI {metrics['roi_percent']:.1f}%")

    # --------------------------------------------------------- 5. explain
    banner("STEP 5/6 — SHAP EXPLAINABILITY")
    from model.explainer import ChargebackExplainer

    explainer = ChargebackExplainer(trainer.model_, trainer.feature_names_)
    explainer.explain_global(X_test.iloc[:3000])
    importance = explainer.get_feature_importance()
    for rank, (feat, score) in enumerate(list(importance.items())[:5], 1):
        print(f"{rank}. {feat:<38} {score:.4f}")

    demo = explainer.explain_single(X_test.iloc[[0]])
    print("\nSample narrative:\n ", demo["explanation_text"])

    # --------------------------------------------- 6. sample full pipeline
    banner("STEP 6/6 — SAMPLE CHARGEBACK THROUGH PRODUCTION PIPELINE")
    from api.routes import LETTER_CACHE, analyze, load_artifacts
    from api.schemas import ChargebackInput

    load_artifacts()
    sample_id = f"CHB-RUN-{uuid.uuid4().hex[:8]}"
    payload = {
        "chargeback_id": sample_id,
        "transaction_id": f"TXN-RUN-{uuid.uuid4().hex[:8]}",
        "transaction_date": date.today() - timedelta(days=18),
        "amount_inr": 14999.0,
        "payment_method": "card_credit",
        "merchant_category": "electronics",
        "chargeback_reason_code": "CB001",
        "merchant_name": "TechNova Retail Pvt Ltd",
        "customer_name": "Ravi Kumar",
        "deadline_date": date.today() + timedelta(days=2),
        "customer_account_age_days": 812,
        "previous_orders_count": 41,
        "previous_chargebacks_count": 0,
        "is_3ds_verified": True,
        "avs_match": True,
        "cvv_match": True,
        "has_delivery_confirmation": True,
        "has_signed_receipt": False,
        "has_login_after_purchase": True,
        "has_support_interaction": False,
        "order_confirmation_sent": True,
        "refund_policy_acknowledged": True,
    }
    result = analyze(ChargebackInput(**payload)).model_dump()
    docx_bytes = LETTER_CACHE.get(sample_id, b"")
    letter_path = PACKAGE_DIR / "model" / "artifacts" / f"sample_letter_{sample_id}.docx"
    letter_path.write_bytes(docx_bytes) if docx_bytes else None

    print(f"Chargeback   : {result['chargeback_id']}")
    print(f"Win prob     : {result['win_probability']:.2%}")
    print(f"Recommendation: {result['recommendation']} ({result['confidence_label']} confidence)")
    print(f"Evidence     : {result['evidence_strength']} ({result['evidence_completeness_pct']:.0f}%)")
    print(f"Recovery est : ₹{result['estimated_recovery_inr']:,.0f}")
    if result["deadline_warning"]:
        print(f"Deadline     : {result['deadline_warning']}")
    print(f"Letter       : {letter_path.name} ({len(docx_bytes):,} bytes)")

    # ------------------------------------------------------------ summary
    elapsed = (datetime.now() - t0).total_seconds()
    banner("PIPELINE SUMMARY")
    print(f"""
Artifacts:
  Dataset      : {csv_path}
  Preprocessor : {pre_pkl}
  Model        : {model_pkl}
  Plots+Report : {PACKAGE_DIR / 'model' / 'artifacts' / 'plots'} + evaluation_report.txt
  Sample letter: {letter_path}

Launch:
  Dashboard : streamlit run dashboard/app.py        -> http://localhost:8501
  API       : uvicorn api.main:app --port 8000      -> http://127.0.0.1:8000/docs

Pipeline finished in {elapsed:.1f}s.
""")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
