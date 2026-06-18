"""Intake subgraph: normalize -> route.

Normalization may pause the run (waiting_for_info). Routing always runs to record
the chosen route, then the subgraph ends. Cross-phase short-circuiting (skipping
enrichment/assessment when paused) is handled by the parent orchestrator.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import normalizer, router
from app.graph.state import RunState


def build_intake_subgraph():
    """Compile and return the intake subgraph."""
    g = StateGraph(RunState)
    g.add_node("normalize", normalizer.normalize)
    g.add_node("route", router.route)
    g.add_edge(START, "normalize")
    g.add_edge("normalize", "route")
    g.add_edge("route", END)
    return g.compile()
