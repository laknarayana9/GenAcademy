"""API-level tests covering the demo surface: /quote, /answers, /reviews.

Each test gets an isolated app instance backed by temp SQLite databases. The
LLM is never required (offline deterministic path). FastAPI BackgroundTasks run
to completion before the TestClient call returns, so a run is already processed
by the time we poll it.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Fresh app with isolated DBs and cleared settings/context caches."""
    monkeypatch.setenv("BUSINESS_DB_PATH", str(tmp_path / "business.db"))
    monkeypatch.setenv("CHECKPOINT_DB_PATH", str(tmp_path / "checkpoints.db"))
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from app.api import deps
    from app.config import get_settings

    get_settings.cache_clear()
    deps._context = None

    from app.api.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client

    deps.shutdown_context()
    get_settings.cache_clear()


# --- payload helpers -------------------------------------------------------
def _accept_payload(**overrides) -> dict:
    payload = {
        "quote_id": "api_accept",
        "applicant_name": "API User",
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
    payload.update(overrides)
    return payload


def _run_detail(client: TestClient, run_id: str) -> dict:
    resp = client.get(f"/runs/{run_id}")
    assert resp.status_code == 200
    return resp.json()


# --- /health ---------------------------------------------------------------
def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


# --- /quote ----------------------------------------------------------------
def test_quote_ho3_accept(client):
    resp = client.post("/quote/ho3", json=_accept_payload())
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    assert resp.json()["status"] == "processing"

    detail = _run_detail(client, run_id)
    assert detail["run"]["status"] == "completed"
    packet = detail["decision_packet"]
    assert packet["recommendation"] == "ACCEPT"
    assert packet["review_status"] == "auto_final"
    assert packet["citations"]  # cited


def test_quote_ho3_validation_error(client):
    bad = _accept_payload()
    bad.pop("state")
    resp = client.post("/quote/ho3", json=bad)
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "Validation failed"
    assert any(fe["field"].endswith("state") for fe in body["field_errors"])


def test_quote_legacy_run(client):
    legacy = {
        "quote_id": "api_legacy",
        "name": "Legacy User",
        "address_state": "TX",
        "zip": "75001",
        "year_built": 2012,
        "construction": "brick",
        "roof": "metal",
        "roof_age": 6,
        "sq_ft": 2000,
        "use": "owner",
        "coverage_a": 350000,
        "deductible": 1000,
    }
    resp = client.post("/quote/run", json=legacy)
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    detail = _run_detail(client, run_id)
    assert detail["run"]["status"] == "completed"
    assert detail["decision_packet"]["recommendation"] == "ACCEPT"


def test_quote_decline_routes_to_review(client):
    resp = client.post(
        "/quote/ho3", json=_accept_payload(quote_id="api_vacant", occupancy="vacant")
    )
    run_id = resp.json()["run_id"]
    detail = _run_detail(client, run_id)
    assert detail["run"]["status"] == "pending_review"
    assert detail["decision_packet"]["recommendation"] == "DECLINE"


# --- /answers --------------------------------------------------------------
def test_answers_resume_flow(client):
    payload = _accept_payload(quote_id="api_missing")
    payload.pop("roof_age_years")
    run_id = client.post("/quote/ho3", json=payload).json()["run_id"]

    detail = _run_detail(client, run_id)
    assert detail["run"]["status"] == "waiting_for_info"
    fields = {q["field"] for q in detail["required_questions"]}
    assert "roof_age_years" in fields

    resume = client.post(
        f"/runs/{run_id}/answers", json={"answers": {"roof_age_years": 6}}
    )
    assert resume.status_code == 200
    assert resume.json()["status"] == "completed"

    final = _run_detail(client, run_id)
    assert final["decision_packet"]["recommendation"] == "ACCEPT"


def test_answers_missing_required_field_422(client):
    payload = _accept_payload(quote_id="api_missing2")
    payload.pop("roof_age_years")
    run_id = client.post("/quote/ho3", json=payload).json()["run_id"]
    assert _run_detail(client, run_id)["run"]["status"] == "waiting_for_info"

    resp = client.post(f"/runs/{run_id}/answers", json={"answers": {"unrelated": 1}})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "Missing required answers"
    assert any(fe["field"] == "roof_age_years" for fe in body["field_errors"])


def test_answers_on_non_waiting_run_409(client):
    run_id = client.post("/quote/ho3", json=_accept_payload()).json()["run_id"]
    assert _run_detail(client, run_id)["run"]["status"] == "completed"

    resp = client.post(
        f"/runs/{run_id}/answers", json={"answers": {"roof_age_years": 5}}
    )
    assert resp.status_code == 409
    assert resp.json()["run_id"] == run_id


def test_answers_run_not_found_404(client):
    resp = client.post("/runs/nope/answers", json={"answers": {}})
    assert resp.status_code == 404
    assert resp.json()["run_id"] == "nope"


# --- /reviews --------------------------------------------------------------
def test_reviews_pending_and_action_approve(client):
    run_id = client.post(
        "/quote/ho3", json=_accept_payload(quote_id="api_review", occupancy="vacant")
    ).json()["run_id"]
    assert _run_detail(client, run_id)["run"]["status"] == "pending_review"

    pending = client.get("/reviews/pending").json()["reviews"]
    assert any(t["run_id"] == run_id for t in pending)

    detail = client.get(f"/reviews/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["decision_packet"]["recommendation"] == "DECLINE"

    action = client.post(
        f"/reviews/{run_id}/actions", json={"action": "approve", "note": "ok"}
    )
    assert action.status_code == 200
    assert action.json()["status"] == "completed"
    assert action.json()["review_status"] == "approved"

    # Packet review_status is finalized; task no longer pending.
    assert _run_detail(client, run_id)["decision_packet"]["review_status"] == "approved"
    still_pending = client.get("/reviews/pending").json()["reviews"]
    assert all(t["run_id"] != run_id for t in still_pending)


def test_reviews_request_info_sets_waiting(client):
    run_id = client.post(
        "/quote/ho3",
        json=_accept_payload(quote_id="api_review2", occupancy="vacant"),
    ).json()["run_id"]
    assert _run_detail(client, run_id)["run"]["status"] == "pending_review"

    resp = client.post(
        f"/reviews/{run_id}/actions",
        json={"action": "request_info", "note": "need docs"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "waiting_for_info"


def test_reviews_not_found_404(client):
    resp = client.get("/reviews/missing")
    assert resp.status_code == 404
    assert resp.json()["run_id"] == "missing"
