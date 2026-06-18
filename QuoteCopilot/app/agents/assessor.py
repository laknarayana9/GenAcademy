"""Underwriting Assessor agent.

Applies the deterministic rule engine and rating tool to the canonical
submission. The rules are the source of truth; this agent does not call an LLM.
Writes both the assessment and rating slices of RunState.
"""

from __future__ import annotations

from app.graph.state import RunState, audit
from app.models.submission import HO3CanonicalSubmission
from app.tools import rating, rules

NODE = "assess"


def assess(state: RunState) -> dict:
    """Evaluate eligibility rules and compute a premium indication."""
    canonical = state.get("submission_canonical", {}) or {}
    enrichment = state.get("enrichment", {}) or {}

    try:
        submission = HO3CanonicalSubmission(**canonical)
    except Exception as exc:  # noqa: BLE001
        return {
            "current_node": NODE,
            "status": "failed",
            "events": [audit(NODE, "failed", {"error": str(exc)})],
        }

    rule_result = rules.evaluate(submission, enrichment)
    rating_result = rating.calculate(submission, enrichment)

    assessment = {
        "preliminary_decision": rule_result.preliminary_decision,
        "reason_codes": rule_result.as_dict()["reason_codes"],
        "rule_findings": rule_result.as_dict()["reason_codes"],
        "facts_used": rule_result.facts_used,
        "confidence": rule_result.confidence,
    }

    return {
        "current_node": NODE,
        "assessment": assessment,
        "rating": rating_result.as_dict(),
        "events": [
            audit(
                NODE,
                "completed",
                {
                    "preliminary_decision": rule_result.preliminary_decision,
                    "premium_indication": rating_result.premium_indication,
                },
            )
        ],
    }
