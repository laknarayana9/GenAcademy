"""Retrieval agent.

Runs the enrichment-produced retrieval plan through the hybrid retriever and
writes the deduplicated evidence set into RunState.retrieval. Cannot cite chunks
that were not retrieved — the verifier later enforces this.
"""

from __future__ import annotations

from app.graph.state import RunState, audit
from app.tools.rag import get_retriever

NODE = "retrieve"


def retrieve(state: RunState) -> dict:
    """Retrieve guideline evidence for the current retrieval plan."""
    enrichment = state.get("enrichment", {}) or {}
    plan = enrichment.get("retrieval_plan", {})

    retriever = get_retriever()
    result = retriever.retrieve_plan(plan)

    return {
        "current_node": NODE,
        "retrieval": result,
        "events": [
            audit(
                NODE,
                "completed",
                {
                    "unique_chunks": result["retrieval_metrics"]["unique_chunks"],
                    "sources": result["source_metadata"],
                },
            )
        ],
    }
