"""Critic agent (optional).

Independently reviews the draft decision packet for completeness, faithfulness,
and consistency. Enabled via CRITIC_ENABLED. Can request a revision or route to
review but cannot change the governed decision itself.
"""

from __future__ import annotations

import json

from app.graph.state import RunState, audit
from app.llm.factory import complete_text

NODE = "critic"


def _deterministic_critique(packet: dict) -> dict:
    """Structural checks that do not require an LLM."""
    issues: list[str] = []
    if not packet.get("recommendation"):
        issues.append("missing_recommendation")
    if not packet.get("reason_codes"):
        issues.append("no_reason_codes")
    if packet.get("recommendation") != "ACCEPT" and not packet.get("citations"):
        issues.append("non_accept_without_citations")
    return {"passed": not issues, "issues": issues}


def critique(state: RunState) -> dict:
    """Critique the current decision packet."""
    packet = state.get("decision_packet", {}) or {}
    base = _deterministic_critique(packet)

    # Optional LLM critique layered on top of deterministic checks.
    system = (
        "You are a critical underwriting reviewer. Given a decision packet, "
        "respond with strict JSON {\"passed\": bool, \"issues\": [str]}. Flag "
        "only genuine completeness or faithfulness problems."
    )
    user = json.dumps(
        {
            "recommendation": packet.get("recommendation"),
            "reason_codes": [c.get("code") for c in packet.get("reason_codes", [])],
            "citations": len(packet.get("citations", [])),
            "next_steps": packet.get("next_steps", []),
        }
    )
    fallback = json.dumps(base)
    raw = complete_text("critic", system, user, fallback)
    try:
        llm_view = json.loads(raw)
        passed = bool(llm_view.get("passed", base["passed"])) and base["passed"]
        issues = sorted(set(base["issues"]) | set(llm_view.get("issues", [])))
    except Exception:  # noqa: BLE001
        passed, issues = base["passed"], base["issues"]

    critique_result = {"passed": passed, "issues": issues}
    verification = dict(state.get("verification", {}) or {})
    if not passed:
        flags = list(verification.get("review_flags", []))
        flags.append("critic_rejected")
        verification["review_flags"] = flags
        verification["review_required"] = True

    return {
        "current_node": NODE,
        "verification": verification,
        "events": [audit(NODE, "completed", critique_result)],
    }
