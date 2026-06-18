"""Enrichment subgraph: enrich -> (retrieve | pause).

If enrichment surfaces a contextual wildfire-mitigation gap it pauses the run and
ends without retrieving. Otherwise it proceeds to retrieval.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import enrichment, retrieval
from app.graph.state import RunState


def _after_enrich(state: RunState) -> str:
    if state.get("status") == "waiting_for_info":
        return "pause"
    return "retrieve"


def build_enrichment_subgraph():
    """Compile and return the enrichment subgraph."""
    g = StateGraph(RunState)
    g.add_node("enrich", enrichment.enrich)
    g.add_node("retrieve", retrieval.retrieve)
    g.add_edge(START, "enrich")
    g.add_conditional_edges(
        "enrich", _after_enrich, {"pause": END, "retrieve": "retrieve"}
    )
    g.add_edge("retrieve", END)
    return g.compile()
