"""Decision Packager agent.

Assembles the final, cited decision packet from the assessment, rating,
retrieved evidence, and verification result. Selects citations only from the
retrieved evidence set (no fabrication). The LLM phrases next steps with a
deterministic fallback.
"""

from __future__ import annotations

from app.graph.state import RunState, audit
from app.llm.factory import complete_text
from app.models.decision import Recommendation, ReviewStatus

NODE = "package"


def _citations_for(reason_codes: list[dict], chunks: list[dict]) -> list[dict]:
    """Pick retrieved chunks that mention each reason code; ensure coverage."""
    selected: dict[str, dict] = {}
    codes = [f.get("code", "") for f in reason_codes]
    for chunk in chunks:
        text = (chunk.get("text") or "").lower()
        if any(code and code.lower() in text for code in codes):
            selected[chunk["chunk_id"]] = chunk
    # Always include at least one general eligibility citation if available.
    if not selected and chunks:
        selected[chunks[0]["chunk_id"]] = chunks[0]
    return list(selected.values())


def _next_steps(recommendation: str, review_required: bool) -> list[str]:
    base = {
        "ACCEPT": ["Bind coverage subject to standard verification."],
        "REFER": ["Route to underwriting review with the referral reason codes."],
        "DECLINE": ["Issue decline notice citing the knockout reason code(s)."],
    }.get(recommendation, ["Route to underwriting review."])
    if review_required and recommendation == "ACCEPT":
        base.append("Confirm verification flags before final issuance.")
    return base


def package(state: RunState) -> dict:
    """Build the decision packet."""
    assessment = state.get("assessment", {}) or {}
    verification = state.get("verification", {}) or {}
    rating = state.get("rating", {}) or {}
    retrieval = state.get("retrieval", {}) or {}
    run_id = state.get("run_id", "")

    recommendation = (
        verification.get("forced_decision")
        or assessment.get("preliminary_decision")
        or "REFER"
    )
    review_required = verification.get("review_required", False)
    reason_codes = assessment.get("reason_codes", [])
    chunks = retrieval.get("chunks", []) or []
    citations = _citations_for(reason_codes, chunks)

    # Narrative next steps (LLM optional).
    fallback_steps = _next_steps(recommendation, review_required)
    system = (
        "You are an underwriting assistant. Given a recommendation and reason "
        "codes, list concise next steps, one per line. Do not invent facts."
    )
    user = (
        f"Recommendation: {recommendation}\n"
        f"Reason codes: {[f.get('code') for f in reason_codes]}\n"
        f"Review required: {review_required}"
    )
    narrative = complete_text("packager", system, user, "\n".join(fallback_steps))
    next_steps = [ln.strip("-• ").strip() for ln in narrative.splitlines() if ln.strip()]
    if not next_steps:
        next_steps = fallback_steps

    review_status = (
        ReviewStatus.PENDING_REVIEW.value
        if review_required
        else ReviewStatus.AUTO_FINAL.value
    )

    packet = {
        "run_id": run_id,
        "recommendation": Recommendation(recommendation).value,
        "confidence": assessment.get("confidence", 0.5),
        "reason_codes": reason_codes,
        "citations": citations,
        "facts_used": {
            **assessment.get("facts_used", {}),
            "rating_factors": rating.get("rating_factors", {}),
        },
        "premium_indication": rating.get("premium_indication"),
        "next_steps": next_steps,
        "review_status": review_status,
    }

    return {
        "current_node": NODE,
        "decision_packet": packet,
        "events": [
            audit(
                NODE,
                "completed",
                {
                    "recommendation": packet["recommendation"],
                    "citations": len(citations),
                    "review_status": review_status,
                },
            )
        ],
    }
