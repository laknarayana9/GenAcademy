"""Planner / Router agent.

Decides the next workflow route from missing-information status and early
knockout signals. Routing is deterministic; the LLM is not involved because
routing governs whether a human must be engaged.
"""

from __future__ import annotations

from app.graph.state import RunState, audit
from app.models.submission import OccupancyType

NODE = "route"


def route(state: RunState) -> dict:
    """Set ``route`` based on missing info and early eligibility signals."""
    if state.get("status") == "waiting_for_info" or state.get("missing_info"):
        return {
            "current_node": NODE,
            "route": "waiting_for_info",
            "events": [audit(NODE, "completed", {"route": "waiting_for_info"})],
        }

    canonical = state.get("submission_canonical", {}) or {}
    occupancy = canonical.get("occupancy")

    if occupancy == OccupancyType.VACANT.value:
        decided = "hard_decline_candidate"
    elif occupancy == OccupancyType.RENTAL.value:
        decided = "hard_refer"
    else:
        decided = "standard"

    return {
        "current_node": NODE,
        "route": decided,
        "events": [audit(NODE, "completed", {"route": decided})],
    }
