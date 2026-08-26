"""Evidence strength scoring.

Converts a raw evidence bundle into a completeness score, a STRONG /
MODERATE / WEAK label, gap analysis against Tier-1 (must-have) evidence,
a merchant-friendly recommendation paragraph and an estimated win-probability
boost derived from the same bonus structure used to synthesise the dataset.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import yaml

PACKAGE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PACKAGE_DIR / "config.yaml"
DATASET_PATH = PACKAGE_DIR / "data" / "chargebacks_synthetic.csv"

EVIDENCE_FIELDS = [
    "is_3ds_verified",
    "has_delivery_confirmation",
    "avs_match",
    "cvv_match",
    "has_signed_receipt",
    "has_login_after_purchase",
    "has_support_interaction",
    "order_confirmation_sent",
    "refund_policy_acknowledged",
]

TIER_1_EVIDENCE = ["is_3ds_verified", "has_delivery_confirmation", "avs_match", "cvv_match"]

EVIDENCE_WIN_BONUS = {
    "is_3ds_verified": 0.20,
    "has_delivery_confirmation": 0.15,
    "has_signed_receipt": 0.12,
    "avs_match": 0.10,
    "cvv_match": 0.08,
    "has_login_after_purchase": 0.07,
    "has_support_interaction": 0.05,
}

FRIENDLY_NAMES = {
    "is_3ds_verified": "3-D Secure verification",
    "has_delivery_confirmation": "courier delivery confirmation",
    "avs_match": "billing address match",
    "cvv_match": "card security code match",
    "has_signed_receipt": "signed proof of delivery",
    "has_login_after_purchase": "post-purchase account login",
    "has_support_interaction": "customer support interaction",
    "order_confirmation_sent": "order confirmation email",
    "refund_policy_acknowledged": "refund policy acknowledgement",
}


class EvidenceScorer:
    """Scores evidence bundles and benchmarks them against winning cases."""

    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        with open(config_path, "r", encoding="utf-8") as fh:
            self.config = yaml.safe_load(fh)
        self._winner_rates_: dict[str, float] | None = None

    # ---------------------------------------------------------------- scoring

    def score(
        self, bundle: dict[str, Any], config_weights: dict[str, float] | None = None
    ) -> dict[str, Any]:
        weights = config_weights or self.config["evidence_weights"]

        completeness = sum(
            float(weights.get(f, 0.0)) for f in EVIDENCE_FIELDS if bundle.get(f)
        )
        present = [f for f in EVIDENCE_FIELDS if bundle.get(f)]
        missing = [f for f in EVIDENCE_FIELDS if not bundle.get(f)]
        missing_critical = [f for f in TIER_1_EVIDENCE if not bundle.get(f)]

        if completeness > 0.7:
            label, emoji = "STRONG", "\U0001F4AA"
        elif completeness >= 0.4:
            label, emoji = "MODERATE", "\U0001F7E1"
        else:
            label, emoji = "WEAK", "\u26A0\uFE0F"

        boost = sum(w for f, w in EVIDENCE_WIN_BONUS.items() if bundle.get(f))
        recommendation_text = self._compose_recommendation(
            completeness, label, present, missing, missing_critical
        )

        return {
            "completeness_score": round(completeness, 3),
            "strength_label": label,
            "strength_emoji": emoji,
            "present_evidence": present,
            "missing_evidence": missing,
            "missing_critical": missing_critical,
            "recommendation_text": recommendation_text,
            "estimated_win_boost": round(boost, 3),
        }

    def _compose_recommendation(
        self,
        completeness: float,
        label: str,
        present: list[str],
        missing: list[str],
        missing_critical: list[str],
    ) -> str:
        pct = int(round(completeness * 100))
        parts = [f"Your evidence package is {label} ({pct}% complete)."]

        strengths = [FRIENDLY_NAMES[f] for f in present[:4]]
        if strengths:
            head = ", ".join(strengths[:-1]) + f" and {strengths[-1]}" if len(strengths) > 1 else strengths[0]
            parts.append(f"You have {head} on record.")

        if not missing_critical:
            parts.append("All four critical proof points are covered, which gives you a solid footing.")
        elif missing_critical:
            names = [FRIENDLY_NAMES[f] for f in missing_critical]
            if len(names) == 1:
                joined = names[0]
                verb = "is"
            else:
                joined = ", ".join(names[:-1]) + f" and {names[-1]}"
                verb = "are"
            parts.append(f"However, {joined} {verb} MISSING — secure this first; banks weigh it heavily.")

        minor_missing = [f for f in missing if f not in missing_critical][:2]
        for f in minor_missing:
            if f == "has_signed_receipt":
                parts.append("The missing signed receipt is acceptable so long as courier tracking confirms delivery.")
            elif f == "has_support_interaction":
                parts.append("A support ticket from the customer would have further signalled genuine engagement.")
            elif f == "has_login_after_purchase":
                parts.append("Post-purchase login activity would strengthen the authorisation story.")
            else:
                parts.append(f"Consider obtaining {FRIENDLY_NAMES[f]} before submitting.")

        if label == "WEAK":
            parts.append("Overall: fighting now is risky — prioritise collecting the missing critical items.")

        return " ".join(parts)

    # ------------------------------------------------------------- benchmark

    def compare_to_winning_cases(self, bundle: dict[str, Any]) -> dict[str, Any]:
        rates = self._winning_rates()
        entries = []
        matched = 0
        for field in EVIDENCE_FIELDS:
            pct_winners = rates[field]
            have = bool(bundle.get(field))
            matched += int(have == (pct_winners >= 50))
            tick = "\u2713" if have else "\u2717"
            verdict = (
                f"{pct_winners:.0f}% of won cases had {FRIENDLY_NAMES[field]}. "
                f"You {'have it' if have else 'do NOT have it'}. {tick}"
            )
            entries.append({
                "evidence": field,
                "friendly_name": FRIENDLY_NAMES[field],
                "pct_of_won_cases": round(pct_winners, 1),
                "you_have_it": have,
                "verdict": verdict,
            })
        alignment = sum(
            min(e["pct_of_won_cases"], 100.0) for e in entries if e["you_have_it"]
        ) / max(sum(min(e["pct_of_won_cases"], 100.0) for e in entries), 1.0)
        return {
            "per_evidence": entries,
            "alignment_with_winners_pct": round(alignment * 100, 1),
        }

    def _winning_rates(self) -> dict[str, float]:
        if self._winner_rates_ is None:
            df = pd.read_csv(DATASET_PATH, usecols=["win_outcome", *EVIDENCE_FIELDS])
            winners = df[df["win_outcome"] == 1]
            self._winner_rates_ = {
                f: float(winners[f].mean()) * 100 for f in EVIDENCE_FIELDS
            }
        return self._winner_rates_


def main() -> int:
    import sys

    PACKAGE_DIR_ABS = Path(__file__).resolve().parent.parent
    if str(PACKAGE_DIR_ABS) not in sys.path:
        sys.path.insert(0, str(PACKAGE_DIR_ABS))
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    from evidence.collector import EvidenceCollector

    collector = EvidenceCollector(seed=42)
    scorer = EvidenceScorer()

    bundle = collector.collect(
        "TXN-DEMO-9911",
        chargeback_data={
            "is_3ds_verified": True,
            "avs_match": True,
            "cvv_match": False,
            "customer_name": "Ravi Kumar",
            "days_since_transaction": 45,
        },
    )
    print("--- COLLECTED BUNDLE ---")
    for line in collector.get_evidence_summary(bundle):
        mark = "[+]" if line["found"] else "[-]"
        preview = f" | {line['metadata_preview']}" if line["metadata_preview"] else ""
        print(f"{mark} {line['name']:<28} ({line['strength']}){preview}")

    result = scorer.score(bundle)
    print("\n--- SCORE ---")
    for key, val in result.items():
        if key != "recommendation_text":
            print(f"  {key}: {val}")
    print(f"\nRecommendation:\n  {result['recommendation_text']}")

    comparison = scorer.compare_to_winning_cases(bundle)
    print("\n--- VS WINNING CASES "
          f"(alignment {comparison['alignment_with_winners_pct']}%) ---")
    for e in comparison["per_evidence"]:
        print(f"  {e['verdict']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
