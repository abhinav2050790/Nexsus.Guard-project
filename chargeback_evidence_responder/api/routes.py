"""API route handlers — the full analysis pipeline in one call."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

PACKAGE_DIR = Path(__file__).resolve().parent.parent
if str(PACKAGE_DIR) not in sys.path:
    sys.path.insert(0, str(PACKAGE_DIR))

import yaml
from fastapi import APIRouter

from api.schemas import AnalysisResult, ChargebackInput
from data.generator import MERCHANT_CATEGORY_WIN_RATES
from data.preprocessor import ChargebackPreprocessor
from evidence.collector import EvidenceCollector
from evidence.scorer import EvidenceScorer
from model.explainer import ChargebackExplainer
from model.trainer import ChargebackModelTrainer
from responder.letter_generator import RebuttalLetterGenerator
from utils.db import db_manager
from utils.logger import get_logger

logger = get_logger()

router = APIRouter()

LETTER_CACHE: dict[str, bytes] = {}

REASON_CODE_WIN_RATES = {"CB001": 0.72, "CB002": 0.58, "CB003": 0.45, "CB004": 0.81}


class PipelineState:
    def __init__(self) -> None:
        self.preprocessor: ChargebackPreprocessor | None = None
        self.trainer: ChargebackModelTrainer | None = None
        self.explainer: ChargebackExplainer | None = None
        self.generator: RebuttalLetterGenerator | None = None
        self.scorer = EvidenceScorer()
        self.collector = EvidenceCollector()
        with open(PACKAGE_DIR / "config.yaml", "r", encoding="utf-8") as fh:
            self.config = yaml.safe_load(fh)
        self.model_metrics: dict[str, float] = {}

    @property
    def ready(self) -> bool:
        return (
            self.preprocessor is not None
            and self.trainer is not None
            and self.trainer.model_ is not None
        )


state = PipelineState()


def load_artifacts() -> None:
    state.preprocessor = ChargebackPreprocessor.load(
        PACKAGE_DIR / "model" / "artifacts" / "preprocessor.pkl"
    )
    state.trainer = ChargebackModelTrainer.load_model(
        PACKAGE_DIR / "model" / "artifacts" / "model.pkl"
    )
    state.explainer = ChargebackExplainer(
        state.trainer.model_, state.trainer.feature_names_
    )
    state.generator = RebuttalLetterGenerator(config_path=PACKAGE_DIR / "config.yaml")
    state.model_metrics = _parse_evaluation_metrics()
    logger.info("API artifacts loaded. Metrics: {}", state.model_metrics)


def _parse_evaluation_metrics() -> dict[str, float]:
    report = PACKAGE_DIR / "model" / "artifacts" / "evaluation_report.txt"
    fallback = {"precision": 0.0, "recall": 0.0, "f1": 0.0, "roc_auc": 0.0}
    if not report.exists():
        return fallback
    text = report.read_text(encoding="utf-8")
    out = {}
    for key, label in [
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1 Score"),
        ("roc_auc", "ROC-AUC"),
    ]:
        m = re.search(rf"{label}\s*:\s*([\d.]+)", text)
        out[key] = float(m.group(1)) if m else 0.0
    return out


def _build_model_row(payload: ChargebackInput) -> pd.DataFrame:
    days_since = max((datetime.now().date() - payload.transaction_date).days, 1)
    merchant_rate = MERCHANT_CATEGORY_WIN_RATES.get(
        payload.merchant_category,
        sum(MERCHANT_CATEGORY_WIN_RATES.values()) / len(MERCHANT_CATEGORY_WIN_RATES),
    )
    reason_rate = REASON_CODE_WIN_RATES[payload.chargeback_reason_code]

    weights = state.config["evidence_weights"]
    completeness = (
        weights["is_3ds_verified"] * payload.is_3ds_verified
        + weights["has_delivery_confirmation"] * payload.has_delivery_confirmation
        + weights["avs_match"] * payload.avs_match
        + weights["cvv_match"] * payload.cvv_match
        + weights["has_signed_receipt"] * payload.has_signed_receipt
        + weights["has_login_after_purchase"] * payload.has_login_after_purchase
        + weights["has_support_interaction"] * payload.has_support_interaction
        + weights["order_confirmation_sent"] * payload.order_confirmation_sent
        + weights["refund_policy_acknowledged"] * payload.refund_policy_acknowledged
    )

    row = {
        "transaction_id": payload.transaction_id,
        "customer_id": f"CUST-API-{payload.chargeback_id}",
        "transaction_date": payload.transaction_date.isoformat(),
        "transaction_amount_inr": float(payload.amount_inr),
        "payment_method": payload.payment_method,
        "merchant_category": payload.merchant_category,
        "chargeback_reason_code": payload.chargeback_reason_code,
        "days_since_transaction": days_since,
        "customer_account_age_days": int(payload.customer_account_age_days),
        "previous_orders_count": int(payload.previous_orders_count),
        "previous_chargebacks_count": int(payload.previous_chargebacks_count),
        "is_high_value_customer": payload.previous_orders_count > 20,
        "is_3ds_verified": bool(payload.is_3ds_verified),
        "avs_match": bool(payload.avs_match),
        "cvv_match": bool(payload.cvv_match),
        "has_delivery_confirmation": bool(payload.has_delivery_confirmation),
        "has_signed_receipt": bool(payload.has_signed_receipt),
        "has_login_after_purchase": bool(payload.has_login_after_purchase),
        "has_support_interaction": bool(payload.has_support_interaction),
        "order_confirmation_sent": bool(payload.order_confirmation_sent),
        "refund_policy_acknowledged": bool(payload.refund_policy_acknowledged),
        "evidence_completeness_score": round(float(completeness), 3),
        "merchant_historical_win_rate": merchant_rate,
        "reason_code_historical_win_rate": reason_rate,
        "win_outcome": 0,
        "split": "train",
    }
    return pd.DataFrame([row])


def _recommendation_for(p: float, thresholds: dict[str, Any]) -> tuple[str, str, str]:
    fight = float(thresholds["fight_above"])
    skip = float(thresholds["skip_below"])
    if p >= fight:
        return "FIGHT", "green", ("HIGH" if p >= 0.75 else "MEDIUM")
    if p >= skip:
        low, high = float(thresholds["review_between"][0]), float(thresholds["review_between"][1])
        band_mid = (low + high) / 2
        confidence = "MEDIUM"
        if abs(p - band_mid) <= 0.05:
            confidence = "LOW"
        return "REVIEW", "yellow", confidence
    return "SKIP", "red", ("HIGH" if p <= 0.15 else "MEDIUM")


@router.post("/analyze", response_model=AnalysisResult)
def analyze(payload: ChargebackInput) -> AnalysisResult:
    if not state.ready:
        load_artifacts()

    row_df = _build_model_row(payload)
    X, _ = state.preprocessor.transform(row_df)

    win_prob = float(state.trainer.model_.predict_proba(X)[0, 1])
    recommendation, color, confidence = _recommendation_for(
        win_prob, state.config["thresholds"]
    )

    bundle = state.collector.collect(
        payload.transaction_id, chargeback_data=payload.model_dump()
    )
    scored = state.scorer.score(bundle)
    explanation = state.explainer.explain_single(X.iloc[[0]])

    costs = state.config["costs"]
    recovery = win_prob * float(payload.amount_inr) * 0.8
    fp_cost_risk = (1 - win_prob) * (
        costs["chargeback_fee_inr"] + costs["response_effort_inr"]
    )

    letter_chargeback = {
        "chargeback_id": payload.chargeback_id,
        "transaction_date": payload.transaction_date.isoformat(),
        "amount_inr": float(payload.amount_inr),
        "reason_code": payload.chargeback_reason_code,
        "merchant_name": payload.merchant_name,
        "customer_name": payload.customer_name,
        "deadline_date": payload.deadline_date.isoformat(),
    }
    letter_prediction = {
        "win_probability": win_prob,
        "recommendation": recommendation,
        "evidence_strength": scored["strength_label"],
    }
    letter = state.generator.generate(letter_chargeback, bundle, letter_prediction)
    LETTER_CACHE[payload.chargeback_id] = letter.word_doc_bytes

    deadline_warning = None
    days_left = (payload.deadline_date - datetime.now().date()).days
    if days_left < 0:
        deadline_warning = f"Deadline passed {abs(days_left)} day(s) ago!"
    elif days_left <= 3:
        deadline_warning = f"Only {days_left} day(s) left to respond!"

    try:
        db_manager.insert_chargeback({
            "chargeback_id": payload.chargeback_id,
            "transaction_id": payload.transaction_id,
            "transaction_date": datetime.combine(payload.transaction_date, datetime.min.time()),
            "amount_inr": float(payload.amount_inr),
            "reason_code": payload.chargeback_reason_code,
            "merchant_name": payload.merchant_name,
            "customer_name": payload.customer_name,
        })
        db_manager.log_prediction({
            "chargeback_id": payload.chargeback_id,
            "win_probability": round(win_prob, 4),
            "recommendation": recommendation,
            "evidence_strength": scored["strength_label"],
            "evidence_completeness_score": scored["completeness_score"],
            "actual_outcome": None,
            "false_positive_cost_inr": round(fp_cost_risk, 2),
            "letter_generated": True,
        })
        db_manager.save_evidence({
            "chargeback_id": payload.chargeback_id,
            "is_3ds_verified": bool(payload.is_3ds_verified),
            "avs_match": bool(payload.avs_match),
            "cvv_match": bool(payload.cvv_match),
            "has_delivery_confirmation": bool(payload.has_delivery_confirmation),
            "has_signed_receipt": bool(payload.has_signed_receipt),
            "has_login_after_purchase": bool(payload.has_login_after_purchase),
            "has_support_interaction": bool(payload.has_support_interaction),
            "order_confirmation_sent": bool(payload.order_confirmation_sent),
            "refund_policy_acknowledged": bool(payload.refund_policy_acknowledged),
        })
    except Exception as exc:
        logger.warning("DB logging failed for {}: {}", payload.chargeback_id, exc)

    return AnalysisResult(
        chargeback_id=payload.chargeback_id,
        win_probability=round(win_prob, 4),
        recommendation=recommendation,
        recommendation_color=color,
        confidence_label=confidence,
        evidence_strength=scored["strength_label"],
        evidence_completeness_pct=round(scored["completeness_score"] * 100, 1),
        estimated_recovery_inr=round(recovery, 2),
        false_positive_cost_inr=round(fp_cost_risk, 2),
        top_positive_factors=explanation["top_positive_factors"][:3],
        top_negative_factors=explanation["top_negative_factors"][:3],
        explanation_text=explanation["explanation_text"],
        letter_preview=RebuttalLetterGenerator.get_letter_preview(letter, 300),
        missing_critical_evidence=[
            "is_3ds_verified" if f == "is_3ds_verified" else f
            for f in scored["missing_critical"]
        ],
        deadline_warning=deadline_warning,
    )


@router.get("/metrics")
def metrics() -> dict[str, Any]:
    rows = db_manager.get_all_predictions()
    rec_counts = {"FIGHT": 0, "REVIEW": 0, "SKIP": 0}
    total_fp_cost = 0.0
    total_recovery = 0.0
    amounts_by_id: dict[str, dict[str, float]] = {}
    try:
        from sqlalchemy import select
        from utils.db import ChargebackRecord
        with db_manager.SessionLocal() as session:
            for rec in session.execute(select(ChargebackRecord)).scalars():
                amounts_by_id[rec.chargeback_id] = float(rec.amount_inr)
    except Exception as exc:
        logger.warning("Could not fetch amounts: {}", exc)

    for r in rows:
        rec = r.get("recommendation")
        if rec in rec_counts:
            rec_counts[rec] += 1
        total_fp_cost += float(r.get("false_positive_cost_inr") or 0.0)
        amount = amounts_by_id.get(r.get("chargeback_id"), 0.0)
        total_recovery += float(r.get("win_probability") or 0.0) * amount * 0.8

    m = state.model_metrics or _parse_evaluation_metrics()
    return {
        "total_analyzed": len(rows),
        "total_fight": rec_counts["FIGHT"],
        "total_review": rec_counts["REVIEW"],
        "total_skip": rec_counts["SKIP"],
        "estimated_total_fp_cost_inr": round(total_fp_cost, 2),
        "estimated_total_recovery_inr": round(total_recovery, 2),
        "model_precision": m["precision"],
        "model_recall": m["recall"],
        "model_f1": m["f1"],
    }
