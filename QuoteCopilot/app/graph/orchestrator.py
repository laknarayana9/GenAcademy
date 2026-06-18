"""Parent orchestrator composing the four phase subgraphs.

    START -> intake -> enrichment -> assessment -> packaging -> END

Each subgraph is compiled and added as a node. Conditional edges short-circuit
to END when a run is paused (waiting_for_info) or has failed, so downstream
phases never execute on an incomplete run. A SqliteSaver checkpointer is attached
at compile time so the same thread_id (== run_id) can be resumed after answers
are supplied.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.state import RunState
from app.graph.subgraphs import (
    build_assessment_subgraph,
    build_enrichment_subgraph,
    build_intake_subgraph,
    build_packaging_subgraph,
)

_HALTED = {"waiting_for_info", "failed"}


def _continue_or_end(next_node: str):
    """Return a branch function that ends the run if halted."""

    def _branch(state: RunState) -> str:
        return "end" if state.get("status") in _HALTED else "continue"

    return _branch, {"continue": next_node, "end": END}


def build_orchestrator(checkpointer=None):
    """Compile the parent orchestrator graph.

    Parameters
    ----------
    checkpointer:
        A LangGraph checkpointer (e.g. SqliteSaver). When None, the graph is
        compiled without persistence (useful for tests/evals).
    """
    g = StateGraph(RunState)
    g.add_node("intake", build_intake_subgraph())
    g.add_node("enrichment", build_enrichment_subgraph())
    g.add_node("assessment", build_assessment_subgraph())
    g.add_node("packaging", build_packaging_subgraph())

    g.add_edge(START, "intake")

    branch, mapping = _continue_or_end("enrichment")
    g.add_conditional_edges("intake", branch, mapping)
    branch, mapping = _continue_or_end("assessment")
    g.add_conditional_edges("enrichment", branch, mapping)
    branch, mapping = _continue_or_end("packaging")
    g.add_conditional_edges("assessment", branch, mapping)

    g.add_edge("packaging", END)

    return g.compile(checkpointer=checkpointer)
