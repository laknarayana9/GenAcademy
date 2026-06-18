"""Integration tests for the full orchestrator graph (offline, no LLM)."""

from __future__ import annotations


def test_accept_path(run_case, accept_payload):
    final = run_case(accept_payload)
    assert final["status"] == "completed"
    packet = final["decision_packet"]
    assert packet["recommendation"] == "ACCEPT"
    assert packet["review_status"] == "auto_final"


def test_decline_vacant_routes_to_review(run_case, accept_payload):
    payload = dict(accept_payload, occupancy="vacant", quote_id="t_vacant")
    final = run_case(payload)
    assert final["status"] == "pending_review"
    assert final["decision_packet"]["recommendation"] == "DECLINE"


def test_missing_roof_age_pauses_then_resumes(run_case, accept_payload):
    payload = dict(accept_payload, quote_id="t_missing")
    payload.pop("roof_age_years")
    paused = run_case(payload)
    assert paused["status"] == "waiting_for_info"
    assert "roof_age_years" in paused["missing_info"]

    resumed = run_case(payload, answers={"roof_age_years": 6})
    assert resumed["status"] == "completed"
    assert resumed["decision_packet"]["recommendation"] == "ACCEPT"


def test_citations_are_grounded(run_case, accept_payload):
    payload = dict(accept_payload, roof_age_years=25, quote_id="t_refer")
    final = run_case(payload)
    packet = final["decision_packet"]
    retrieved_ids = {c["chunk_id"] for c in final["retrieval"]["chunks"]}
    for citation in packet["citations"]:
        assert citation["chunk_id"] in retrieved_ids


def test_wildfire_mitigation_followup(run_case, accept_payload):
    payload = dict(
        accept_payload, state="CA", zip_code="95014", quote_id="t_wildfire"
    )
    payload.pop("roof_age_years", None)
    payload["roof_age_years"] = 7
    paused = run_case(payload)
    assert paused["status"] == "waiting_for_info"
    assert "wildfire_mitigation" in paused["missing_info"]
