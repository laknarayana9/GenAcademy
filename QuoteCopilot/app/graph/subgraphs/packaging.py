"""Packaging subgraph: package -> [critic] -> route_decision -> [review].

CRITIC_ENABLED is read once at compile time and baked into the graph as a static
branch (not a state field). The critic, when enabled, can flag the packet for
review but cannot alter the governed decision. route_decision finalizes the run
status: ``completed`` for auto-final packets, ``pending_review`` when review is
required (which also creates a review task downstream).
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import critic, packager
from app.config import get_settings
from app.graph.state import RunState, audit
from app.models.review import ReviewPriority, ReviewTrigger

NODE_ROUTE = "route_decision"
NODE_REVIEW = "create_review_task"


def _route_decision(state: RunState) -> dict:
    """Set terminal status based on whether review is required."""
    verification = state.get("verification", {}) or {}
    review_required = verification.get("review_required", False)
    status = "pending_review" if review_required else "completed"
    return {
        "current_node": NODE_ROUTE,
        "status": status,
        "events": [audit(NODE_ROUTE, "completed", {"status": status})],
    }


def _review_branch(state: RunState) -> str:
    return "review" if state.get("status") == "pending_review" else "done"


def _trigger_for(state: RunState) -> str:
    decision = (state.get("assessment", {}) or {}).get("preliminary_decision", "")
    flags = (state.get("verification", {}) or {}).get("review_flags", [])
    if decision == "DECLINE":
        return ReviewTrigger.DECLINE.value
    if decision == "REFER":
        return ReviewTrigger.REFER.value
    if any(f.startswith("ungrounded") or f == "no_evidence_retrieved" for f in flags):
        return ReviewTrigger.VERIFICATION_FAILURE.value
    return ReviewTrigger.REFER.value


def _create_review_task(state: RunState) -> dict:
    """Attach review-task metadata to verification for the runner to persist."""
    trigger = _trigger_for(state)
    priority = (
        ReviewPriority.HIGH.value
        if trigger in {ReviewTrigger.DECLINE.value, ReviewTrigger.VERIFICATION_FAILURE.value}
        else ReviewPriority.MEDIUM.value
    )
    verification = dict(state.get("verification", {}) or {})
    canonical = state.get("submission_canonical", {}) or {}
    submission_summary = {
        k: canonical.get(k)
        for k in (
            "applicant_name", "state", "zip_code", "year_built",
            "construction_type", "roof_type", "roof_age_years",
            "square_feet", "occupancy", "coverage",
        )
    }
    verification["review_task"] = {
        "trigger": trigger,
        "priority": priority,
        "review_packet": {
            "recommendation": (state.get("decision_packet", {}) or {}).get(
                "recommendation"
            ),
            "reason_codes": (state.get("decision_packet", {}) or {}).get(
                "reason_codes", []
            ),
            "review_flags": verification.get("review_flags", []),
            "submission": submission_summary,
        },
    }
    return {
        "current_node": NODE_REVIEW,
        "verification": verification,
        "events": [audit(NODE_REVIEW, "completed", {"trigger": trigger})],
    }


def build_packaging_subgraph():
    """Compile and return the packaging subgraph."""
    settings = get_settings()
    g = StateGraph(RunState)
    g.add_node("package", packager.package)
    g.add_node(NODE_ROUTE, _route_decision)
    g.add_node(NODE_REVIEW, _create_review_task)
    g.add_edge(START, "package")

    if settings.critic_enabled:
        g.add_node("critic", critic.critique)
        g.add_edge("package", "critic")
        g.add_edge("critic", NODE_ROUTE)
    else:
        g.add_edge("package", NODE_ROUTE)

    g.add_conditional_edges(
        NODE_ROUTE, _review_branch, {"review": NODE_REVIEW, "done": END}
    )
    g.add_edge(NODE_REVIEW, END)
    return g.compile()
