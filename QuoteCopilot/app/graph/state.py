"""Shared graph state schema.

One `RunState` TypedDict flows through the parent orchestrator and every
subgraph. Subgraphs read and write the same schema, so no mapping layer is
needed. `thread_id` maps 1:1 to `run_id`. The `events` field uses an additive
reducer so audit events accumulate across nodes rather than being overwritten.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class RunState(TypedDict, total=False):
    """Durable per-run state carried across the workflow."""

    run_id: str
    quote_id: str
    status: str               # processing|waiting_for_info|pending_review|completed|failed
    current_node: str
    route: str                # standard|waiting_for_info|hard_refer|hard_decline_candidate

    submission_raw: dict
    submission_canonical: dict

    missing_info: list[str]
    required_questions: list[dict]
    additional_answers: dict

    enrichment: dict          # property_profile, hazard_profile, retrieval_plan
    retrieval: dict           # chunks, source_metadata, retrieval_metrics
    assessment: dict          # rule_findings, preliminary_decision, reason_codes, confidence
    verification: dict        # grounding_result, review_flags, forced_decision
    rating: dict              # premium_indication, rating_factors
    decision_packet: dict     # recommendation, confidence, citations, next_steps, review_status

    events: Annotated[list[dict], operator.add]


def new_run_state(run_id: str, quote_id: str, submission_raw: dict) -> RunState:
    """Construct an initial RunState for a fresh run."""
    return RunState(
        run_id=run_id,
        quote_id=quote_id,
        status="processing",
        current_node="start",
        route="standard",
        submission_raw=submission_raw,
        submission_canonical={},
        missing_info=[],
        required_questions=[],
        additional_answers={},
        enrichment={},
        retrieval={},
        assessment={},
        verification={},
        rating={},
        decision_packet={},
        events=[],
    )


def audit(node: str, event_type: str, payload: dict | None = None) -> dict:
    """Build a single audit event entry for the additive ``events`` channel."""
    return {"node": node, "event_type": event_type, "payload": payload or {}}
