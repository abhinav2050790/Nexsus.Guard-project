"""Simulated evidence collection engine.

In production this module would call courier APIs, bank authorisation logs
and CRM systems. Here it deterministically simulates those sources: values
present in ``chargeback_data`` are honoured verbatim, anything absent is
simulated with realistic priors and rich metadata suitable for rebuttal
letters and dashboard previews.
"""

from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from typing import Any

from evidence.scorer import EvidenceScorer
from utils.logger import get_logger

logger = get_logger()

COURIERS = ["BlueDart", "Delhivery", "DTDC", "Ekart Logistics", "India Post"]
TICKET_SUBJECTS = [
    "Where is my order?",
    "Invoice copy requested",
    "Product specification query",
    "Delivery reschedule request",
    "Refund status enquiry",
]
SIGNER_NAMES = [
    "R. Sharma", "P. Verma", "A. Iyer", "S. Nair", "M. Khan",
    "K. Reddy", "D. Joshi", "V. Pillai", "N. Gupta", "T. Bose",
]


def _rand_ip(rng: random.Random) -> str:
    octets = [rng.choice([49, 103, 117, 106, 182]), rng.randint(0, 255),
              rng.randint(0, 255), rng.randint(1, 254)]
    return ".".join(map(str, octets))


def _tracking_number(rng: random.Random) -> str:
    return "TRK" + "".join(rng.choices(string.digits, k=9))


def _slug_email(name: str | None, txn_id: str) -> str:
    if name:
        slug = "".join(ch.lower() for ch in name.split()[0] if ch.isalpha())
    else:
        slug = "customer"
    suffix = "".join(ch for ch in txn_id if ch.isdigit())[-5:] or "00000"
    return f"{slug}.{suffix}@example.com"


class EvidenceCollector:
    """Collects (simulated) proof artefacts for a disputed transaction."""

    def __init__(self, seed: int | None = None, scorer: EvidenceScorer | None = None) -> None:
        self.rng = random.Random(seed)
        self.scorer = scorer or EvidenceScorer()
        self.now = datetime.now()

    # -------------------------------------------------------------- helpers

    def _value_or_simulate(
        self, chargeback_data: dict[str, Any], field: str, prior_p: float
    ) -> bool:
        if field in chargeback_data and chargeback_data[field] is not None:
            return bool(chargeback_data[field])
        return self.rng.random() < prior_p

    # --------------------------------------------------------------- collect

    def collect(
        self, transaction_id: str, chargeback_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        data = dict(chargeback_data or {})
        rng = self.rng

        is_3ds = self._value_or_simulate(data, "is_3ds_verified", 0.70)
        avs = self._value_or_simulate(data, "avs_match", 0.65)
        cvv = self._value_or_simulate(data, "cvv_match", 0.80)

        has_delivery = self._value_or_simulate(data, "has_delivery_confirmation", 0.60)
        has_signed = has_delivery and self._value_or_simulate(data, "has_signed_receipt", 0.40)
        has_login = self._value_or_simulate(data, "has_login_after_purchase", 0.55)
        has_support = self._value_or_simulate(data, "has_support_interaction", 0.30)
        confirmation_sent = self._value_or_simulate(data, "order_confirmation_sent", 0.85)
        policy_ack = self._value_or_simulate(data, "refund_policy_acknowledged", 0.75)

        days_since = int(data.get("days_since_transaction", rng.randint(5, 120)))
        txn_date = self.now - timedelta(days=days_since)
        email = _slug_email(data.get("customer_name"), transaction_id)

        bundle: dict[str, Any] = {
            "transaction_id": transaction_id,
            "collected_at": self.now.isoformat(timespec="seconds"),
            "is_3ds_verified": is_3ds,
            "avs_match": avs,
            "cvv_match": cvv,
            "has_delivery_confirmation": has_delivery,
            "delivery_metadata": {
                "courier": rng.choice(COURIERS),
                "tracking_number": _tracking_number(rng),
                "delivered_date": (
                    txn_date + timedelta(days=rng.randint(1, min(7, max(1, days_since))))
                ).date().isoformat(),
            } if has_delivery else {},
            "has_signed_receipt": has_signed,
            "signature_metadata": {
                "signer_name": rng.choice(SIGNER_NAMES),
            } if has_signed else {},
            "has_login_after_purchase": has_login,
            "login_metadata": {
                "login_timestamp": (
                    txn_date + timedelta(hours=rng.randint(2, 96))
                ).isoformat(timespec="seconds"),
                "ip_address": _rand_ip(rng),
            } if has_login else {},
            "has_support_interaction": has_support,
            "support_metadata": {
                "ticket_id": "TKT-" + "".join(rng.choices(string.digits, k=6)),
                "subject": rng.choice(TICKET_SUBJECTS),
                "created_date": (
                    txn_date + timedelta(days=rng.randint(0, 3))
                ).date().isoformat(),
            } if has_support else {},
            "order_confirmation_sent": confirmation_sent,
            "confirmation_metadata": {
                "email": email,
                "sent_timestamp": txn_date.isoformat(timespec="seconds"),
            } if confirmation_sent else {},
            "refund_policy_acknowledged": policy_ack,
        }

        scored = self.scorer.score(bundle)
        completeness = scored["completeness_score"]
        bundle["collection_status"] = (
            "COMPLETE" if completeness > 0.7 else
            "PARTIAL" if completeness >= 0.4 else
            "MINIMAL"
        )

        logger.info(
            "Evidence collected for {} — status {} ({:.0%} complete)",
            transaction_id, bundle["collection_status"], completeness,
        )
        return bundle

    # --------------------------------------------------------------- summary

    def get_evidence_summary(self, bundle: dict[str, Any]) -> list[dict[str, Any]]:
        weights = self.scorer.config["evidence_weights"]

        def strength_for(field: str) -> str:
            w = float(weights.get(field, 0.0))
            if w >= 0.15:
                return "CRITICAL"
            if w >= 0.07:
                return "IMPORTANT"
            return "SUPPLEMENTARY"

        rows = []
        for field in [
            "is_3ds_verified",
            "has_delivery_confirmation",
            "avs_match",
            "cvv_match",
            "has_signed_receipt",
            "has_login_after_purchase",
            "has_support_interaction",
            "order_confirmation_sent",
            "refund_policy_acknowledged",
        ]:
            found = bool(bundle.get(field))
            meta_key = {
                "has_delivery_confirmation": "delivery_metadata",
                "has_signed_receipt": "signature_metadata",
                "has_login_after_purchase": "login_metadata",
                "has_support_interaction": "support_metadata",
                "order_confirmation_sent": "confirmation_metadata",
            }.get(field)
            meta = bundle.get(meta_key, {}) if meta_key else {}
            preview = " · ".join(str(v) for v in meta.values()) if meta else ""
            rows.append({
                "name": field,
                "found": found,
                "strength": strength_for(field),
                "metadata_preview": preview,
            })
        return rows


if __name__ == "__main__":
    import sys
    from pathlib import Path as _P

    _root = _P(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    collector = EvidenceCollector(seed=7)
    b = collector.collect("TXN-SMOKE-42", {"is_3ds_verified": True})
    print(b["collection_status"])
    for row in collector.get_evidence_summary(b):
        print(row["found"], row["name"], row["metadata_preview"][:60])
