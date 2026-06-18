"""HTTP client for the QuoteCopilot API.

Thin, typed wrappers around every endpoint the UI needs, plus a polling helper.
All network access in the UI funnels through here so pages stay declarative.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

TERMINAL_STATES = {"completed", "pending_review", "waiting_for_info", "failed"}


class ApiError(Exception):
    """Raised when the API returns an error payload or is unreachable."""


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=60)


def health() -> bool:
    try:
        with _client() as c:
            return c.get("/health").json().get("status") == "ok"
    except Exception:  # noqa: BLE001
        return False


def start_ho3(submission: dict) -> dict:
    with _client() as c:
        resp = c.post("/quote/ho3", json=submission)
    data = resp.json()
    if resp.status_code >= 400:
        raise ApiError(data.get("error", "Submission failed"))
    return data


def get_run(run_id: str) -> dict:
    with _client() as c:
        return c.get(f"/runs/{run_id}").json()


def get_audit(run_id: str) -> list[dict]:
    with _client() as c:
        return c.get(f"/runs/{run_id}/audit").json().get("events", [])


def submit_answers(run_id: str, answers: dict[str, Any]) -> dict:
    with _client() as c:
        resp = c.post(f"/runs/{run_id}/answers", json={"answers": answers})
    return resp.json()


def list_runs(limit: int = 50) -> list[dict]:
    with _client() as c:
        return c.get("/runs", params={"limit": limit}).json().get("runs", [])


def pending_reviews() -> list[dict]:
    with _client() as c:
        return c.get("/reviews/pending").json().get("reviews", [])


def get_review(run_id: str) -> dict:
    with _client() as c:
        return c.get(f"/reviews/{run_id}").json()


def apply_action(run_id: str, action: str, note: str = "") -> dict:
    with _client() as c:
        resp = c.post(
            f"/reviews/{run_id}/actions", json={"action": action, "note": note}
        )
    return resp.json()


def poll_run(run_id: str, attempts: int = 40, delay: float = 0.3) -> dict:
    """Poll a run until it reaches a terminal state (or attempts run out)."""
    last = get_run(run_id)
    for _ in range(attempts):
        status = (last.get("run") or {}).get("status")
        if status in TERMINAL_STATES:
            return last
        time.sleep(delay)
        last = get_run(run_id)
    return last
