"""Shared pytest fixtures."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.graph.orchestrator import build_orchestrator  # noqa: E402
from app.graph.state import new_run_state  # noqa: E402


@pytest.fixture(scope="session")
def graph():
    """Compiled orchestrator without a checkpointer (deterministic runs)."""
    return build_orchestrator(checkpointer=None)


@pytest.fixture
def accept_payload() -> dict:
    return {
        "quote_id": "t_accept",
        "applicant_name": "Test User",
        "state": "TX",
        "zip_code": "75001",
        "year_built": 2015,
        "construction_type": "masonry",
        "roof_type": "metal",
        "roof_age_years": 4,
        "square_feet": 2200,
        "occupancy": "owner_primary",
        "coverage": {"dwelling_amount": 400000, "deductible": 1000},
    }


@pytest.fixture
def run_case(graph):
    """Helper to run a raw payload through the graph and return final state."""

    def _run(payload: dict, answers: dict | None = None) -> dict:
        state = new_run_state(payload.get("quote_id", "t"), payload.get("quote_id", "t"), payload)
        if answers:
            state["additional_answers"] = answers
        return graph.invoke(state)

    return _run
