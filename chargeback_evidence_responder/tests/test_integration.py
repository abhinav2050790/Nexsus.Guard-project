"""Integration tests for the Chargeback Evidence Responder.

Run from the package directory:
    pytest tests/test_integration.py -v

The API tests use FastAPI's TestClient, so no running server is required.
"""

from __future__ import annotations

import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

PACKAGE_DIR = Path(__file__).resolve().parent.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

REQUIRED_COLUMNS = {
    "transaction_id", "transaction_date", "transaction_amount_inr",
    "payment_method", "merchant_category", "chargeback_reason_code",
    "days_since_transaction", "customer_id", "customer_account_age_days",
    "previous_orders_count", "previous_chargebacks_count",
    "is_high_value_customer", "is_3ds_verified", "avs_match", "cvv_match",
    "has_delivery_confirmation", "has_signed_receipt",
    "has_login_after_purchase", "has_support_interaction",
    "order_confirmation_sent", "refund_policy_acknowledged",
    "evidence_completeness_score", "merchant_historical_win_rate",
    "reason_code_historical_win_rate", "win_outcome", "split",
}

EVIDENCE_KEYS = [
    "is_3ds_verified", "avs_match", "cvv_match", "has_delivery_confirmation",
    "has_signed_receipt", "has_login_after_purchase", "has_support_interaction",
    "order_confirmation_sent", "refund_policy_acknowledged",
]

TEMPLATE_SLOTS = [
    "{{CHARGEBACK_ID}}", "{{TRANSACTION_DATE}}", "{{AMOUNT_INR}}",
    "{{MERCHANT_NAME}}", "{{CUSTOMER_NAME}}", "{{REASON_CODE}}",
    "{{EVIDENCE_LIST}}", "{{RESPONSE_DATE}}", "{{WIN_PROBABILITY_PCT}}",
    "{{EVIDENCE_STRENGTH}}",
]


@pytest.fixture(scope="session")
def dataset_csv() -> Path:
    path = PACKAGE_DIR / "data" / "chargebacks_synthetic.csv"
    if not path.exists():
        from data.generator import generate_dataset

        generate_dataset().to_csv(path, index=False)
    return path


@pytest.fixture(scope="session")
def fitted_preprocessor(dataset_csv):
    from data.preprocessor import ChargebackPreprocessor

    pre = ChargebackPreprocessor()
    train_df, _, _ = pre.load_data(dataset_csv)
    pre.fit_transform(train_df)
    return pre


@pytest.fixture(scope="session")
def trained_model(fitted_preprocessor, dataset_csv):
    artifact = PACKAGE_DIR / "model" / "artifacts" / "model.pkl"
    if not artifact.exists():
        pytest.skip("model.pkl not found — run `python run_all.py` first")
    from model.trainer import ChargebackModelTrainer

    trainer = ChargebackModelTrainer.load_model(artifact)
    _, _, test_df = fitted_preprocessor.load_data(dataset_csv)
    X_test, y_test = fitted_preprocessor.transform(test_df)
    return trainer, X_test, y_test


@pytest.fixture(scope="session")
def api_client():
    from fastapi.testclient import TestClient

    from api.main import app

    with TestClient(app) as client:
        yield client


# --------------------------------------------------------------------- tests


def test_dataset_generation():
    from data.generator import generate_dataset

    df = generate_dataset(n_samples=1000, seed=42)
    missing = REQUIRED_COLUMNS - set(df.columns)
    assert not missing, f"Missing columns: {missing}"
    assert len(df) == 1000

    win_rate = float(df["win_outcome"].mean())
    assert 0.60 <= win_rate <= 0.95, (
        f"Unexpected class balance: win_rate={win_rate:.2f} "
        "(documented generative range is ~83% wins)"
    )
    assert set(df["split"].unique()) == {"train", "val", "test"}
    assert df["transaction_id"].is_unique


def test_preprocessing(fitted_preprocessor, dataset_csv):
    pre = fitted_preprocessor
    train_df, val_df, test_df = pre.load_data(dataset_csv)

    engineered = pre.engineer_features(train_df.head(500), fit=True)
    for col in [
        "amount_risk_tier", "customer_trust_score", "days_since_bucket",
        "verification_score", "chargeback_risk_flag", "is_first_time_buyer",
        "high_amount_flag", "payment_method_risk", "reason_code_encoded",
    ]:
        assert col in engineered.columns, f"Engineered feature missing: {col}"

    X_train, y_train = pre.fit_transform(train_df)
    X_val, y_val = pre.transform(val_df)
    X_test, _ = pre.transform(test_df)

    assert len(pre.get_feature_columns()) == 27
    assert X_train.shape[1] == 27
    assert X_val.shape == (len(val_df), 27)
    assert X_test.shape == (len(test_df), 27)
    assert set(y_train.unique()) <= {0, 1}
    assert X_train.notna().all().all(), "NaNs found in feature matrix"


def test_model_prediction(trained_model):
    trainer, X_test, _ = trained_model
    sample = X_test.iloc[:10]
    probs = trainer.model_.predict_proba(sample)

    assert probs.shape == (10, 2)
    assert ((probs >= 0.0) & (probs <= 1.0)).all()
    assert float(np.abs(probs.sum(axis=1) - 1.0).max()) < 1e-5
    preds = trainer.model_.predict(sample)
    assert set(preds) <= {0, 1}


def test_evidence_collector():
    from evidence.collector import EvidenceCollector

    collector = EvidenceCollector(seed=123)
    bundle = collector.collect("TXN-PYTEST-001", {"is_3ds_verified": True})

    for key in EVIDENCE_KEYS:
        assert key in bundle, f"Evidence field missing: {key}"
        assert isinstance(bundle[key], bool)
    assert bundle["is_3ds_verified"] is True
    assert bundle["collection_status"] in {"COMPLETE", "PARTIAL", "MINIMAL"}

    summary = collector.get_evidence_summary(bundle)
    assert len(summary) == 9
    assert all({"name", "found", "strength"} <= set(row) for row in summary)


def test_evidence_scorer():
    from evidence.scorer import EvidenceScorer, EVIDENCE_WIN_BONUS

    scorer = EvidenceScorer()
    full_bundle = {key: True for key in EVIDENCE_KEYS}
    result = scorer.score(full_bundle)

    assert result["strength_label"] == "STRONG"
    assert result["completeness_score"] > 0.99
    assert result["missing_critical"] == []
    expected_boost = sum(
        w for f, w in EVIDENCE_WIN_BONUS.items() if f in EVIDENCE_KEYS
    )
    assert np.isclose(result["estimated_win_boost"], expected_boost, atol=1e-6)

    empty = scorer.score({k: False for k in EVIDENCE_KEYS})
    assert empty["strength_label"] == "WEAK"
    assert len(empty["missing_critical"]) == 4
    assert empty["strength_label"] in {"STRONG", "MODERATE", "WEAK"}


def test_letter_generation():
    from responder.letter_generator import RebuttalLetterGenerator

    gen = RebuttalLetterGenerator()
    bundle = {key: True for key in EVIDENCE_KEYS}
    bundle.update({
        "delivery_metadata": {"courier": "BlueDart", "tracking_number": "TRK123456789",
                              "delivered_date": "2026-08-15"},
        "signature_metadata": {"signer_name": "R. Sharma"},
        "login_metadata": {"login_timestamp": "2026-08-12T10:00:00", "ip_address": "49.36.1.2"},
        "confirmation_metadata": {"email": "ravi.00001@example.com",
                                  "sent_timestamp": "2026-08-11T09:00:00"},
    })
    chargeback = {
        "chargeback_id": "CHB-PYTEST-LTR",
        "transaction_date": date(2026, 8, 11),
        "amount_inr": 9999.0,
        "reason_code": "CB001",
        "merchant_name": "TestMart",
        "customer_name": "Ravi Kumar",
        "deadline_date": date.today() + timedelta(days=10),
    }
    prediction = {"win_probability": 0.87, "recommendation": "FIGHT",
                  "evidence_strength": "STRONG"}

    letter = gen.generate(chargeback, bundle, prediction)
    text = letter.letter_text

    assert letter.template_used == "unauthorized.txt"
    for slot in TEMPLATE_SLOTS:
        assert slot not in text, f"Unfilled placeholder: {slot}"
    assert "WITHOUT PREJUDICE" in text
    assert "Yours faithfully," in text
    assert "AI Confidence Score: 87%" in text
    assert letter.word_doc_bytes.startswith(b"PK")
    assert isinstance(letter.missing_evidence_warnings, list)


def test_api_health(api_client):
    resp = api_client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["model_loaded"] is True
    assert body["db_connected"] is True


def test_api_analyze(api_client):
    payload = {
        "chargeback_id": f"CHB-PYTEST-{uuid.uuid4().hex[:8]}",
        "transaction_id": f"TXN-PYTEST-{uuid.uuid4().hex[:8]}",
        "transaction_date": str(date.today() - timedelta(days=14)),
        "amount_inr": 7500.0,
        "payment_method": "upi",
        "merchant_category": "food",
        "chargeback_reason_code": "CB002",
        "merchant_name": "PyTest Foods",
        "customer_name": "Test User",
        "deadline_date": str(date.today() + timedelta(days=5)),
        "customer_account_age_days": 400,
        "previous_orders_count": 12,
        "previous_chargebacks_count": 1,
        "is_3ds_verified": True,
        "avs_match": False,
        "cvv_match": True,
        "has_delivery_confirmation": True,
        "has_signed_receipt": False,
        "has_login_after_purchase": True,
        "has_support_interaction": False,
        "order_confirmation_sent": True,
        "refund_policy_acknowledged": True,
    }
    resp = api_client.post("/analyze", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["chargeback_id"] == payload["chargeback_id"]
    assert 0.0 <= body["win_probability"] <= 1.0
    assert body["recommendation"] in {"FIGHT", "REVIEW", "SKIP"}
    assert body["evidence_strength"] in {"STRONG", "MODERATE", "WEAK"}
    assert body["explanation_text"]
    assert body["letter_preview"]

    health = api_client.get("/download-letter/" + payload["chargeback_id"])
    assert health.status_code == 200
    assert health.content.startswith(b"PK")
