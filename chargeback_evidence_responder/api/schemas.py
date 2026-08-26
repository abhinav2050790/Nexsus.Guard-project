"""Pydantic request/response models for the Chargeback Evidence Responder API."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class ChargebackInput(BaseModel):
    chargeback_id: str
    transaction_id: str
    transaction_date: date
    amount_inr: float = Field(gt=0)
    payment_method: Literal["card_credit", "card_debit", "upi", "netbanking", "wallet"]
    merchant_category: str
    chargeback_reason_code: Literal["CB001", "CB002", "CB003", "CB004"]
    merchant_name: str
    customer_name: str
    deadline_date: date

    customer_account_age_days: int = Field(ge=0)
    previous_orders_count: int = Field(ge=0)
    previous_chargebacks_count: int = Field(ge=0)

    is_3ds_verified: bool
    avs_match: bool
    cvv_match: bool
    has_delivery_confirmation: bool
    has_signed_receipt: bool
    has_login_after_purchase: bool
    has_support_interaction: bool
    order_confirmation_sent: bool
    refund_policy_acknowledged: bool


class AnalysisResult(BaseModel):
    chargeback_id: str
    win_probability: float
    recommendation: str
    recommendation_color: str
    confidence_label: str
    evidence_strength: str
    evidence_completeness_pct: float
    estimated_recovery_inr: float
    false_positive_cost_inr: float
    top_positive_factors: list[dict]
    top_negative_factors: list[dict]
    explanation_text: str
    letter_preview: str
    missing_critical_evidence: list[str]
    deadline_warning: Optional[str] = None
    analyzed_at: datetime = Field(default_factory=datetime.now)


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    status: str
    model_loaded: bool
    db_connected: bool
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseModel):
    error: str
    chargeback_id: str = ""
