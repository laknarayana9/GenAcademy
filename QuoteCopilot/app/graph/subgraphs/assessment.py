"""Assessment subgraph: assess -> verify.

The assessor runs the deterministic rule engine and rating tool (rating is
computed alongside assessment so the verifier can flag incomplete rating). The
verifier then sets grounding and review flags. Fully autonomous — no interrupts.
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agents import assessor, verifier
from app.graph.state import RunState


def _after_assess(state: RunState) -> str:
    return "fail" if state.get("status") == "failed" else "verify"


def build_assessment_subgraph():
    """Compile and return the assessment subgraph."""
    g = StateGraph(RunState)
    g.add_node("assess", assessor.assess)
    g.add_node("verify", verifier.verify)
    g.add_edge(START, "assess")
    g.add_conditional_edges("assess", _after_assess, {"fail": END, "verify": "verify"})
    g.add_edge("verify", END)
    return g.compile()
