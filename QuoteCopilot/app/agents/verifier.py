"""Verifier / Guardrail agent.

Checks that the assessment is grounded in retrieved evidence and decides whether
human review is mandatory. Deterministic: it can force review but never silently
finalizes a REFER or DECLINE.
"""

from __future__ import annotations

from app.graph.state import RunState, audit

NODE = "verify"

_REVIEW_DECISIONS = {"REFER", "DECLINE"}


def verify(state: RunState) -> dict:
    """Produce grounding result and review flags for the assessment."""
    assessment = state.get("assessment", {}) or {}
    retrieval = state.get("retrieval", {}) or {}
    rating = state.get("rating", {}) or {}

    chunks = retrieval.get("chunks", []) or []
    evidence_text = " ".join(c.get("text", "") for c in chunks).lower()
    retrieved_ids = {c.get("chunk_id") for c in chunks}

    review_flags: list[str] = []

    # Grounding: every non-trivial reason code should appear in retrieved text.
    ungrounded: list[str] = []
    for finding in assessment.get("reason_codes", []):
        code = finding.get("code", "")
        if code == "RC-001":  # generic "all passed" needs no citation
            continue
        if code.lower() not in evidence_text:
            ungrounded.append(code)
    if ungrounded:
        review_flags.append("ungrounded_reason_codes")

    if not chunks:
        review_flags.append("no_evidence_retrieved")

    decision = assessment.get("preliminary_decision", "ACCEPT")
    if decision in _REVIEW_DECISIONS:
        review_flags.append(f"decision_{decision.lower()}")

    if rating.get("incomplete"):
        review_flags.append("incomplete_rating")

    # An ACCEPT with no supporting evidence may proceed only if rules are clean.
    forced_decision = None
    if decision == "ACCEPT" and ("no_evidence_retrieved" in review_flags):
        # Deterministic rules support ACCEPT; continue but record the flag.
        pass

    review_required = bool(set(review_flags) - set())  # any flag triggers review

    verification = {
        "grounding_result": {
            "retrieved_ids": sorted(i for i in retrieved_ids if i),
            "ungrounded_reason_codes": ungrounded,
            "evidence_chunks": len(chunks),
        },
        "review_flags": review_flags,
        "forced_decision": forced_decision,
        "review_required": review_required,
    }

    return {
        "current_node": NODE,
        "verification": verification,
        "events": [
            audit(NODE, "completed", {"review_flags": review_flags}),
        ],
    }
