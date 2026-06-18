"""QuoteCopilot Streamlit UI.

A pure rendering + httpx client layer over the FastAPI backend. No business
logic lives here. Four pages map to the demo scenarios: Submit Quote, Answer
Questions, Review Queue, and Audit Trail.
"""

from __future__ import annotations

import json
import os
import time

import httpx
import streamlit as st

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")

DEMO_SCENARIOS = {
    "Straight-through ACCEPT": {
        "quote_id": "DEMO-ACCEPT",
        "applicant_name": "Alex Rivera",
        "state": "TX",
        "zip_code": "75001",
        "year_built": 2015,
        "construction_type": "masonry",
        "roof_type": "metal",
        "roof_age_years": 4,
        "square_feet": 2200,
        "occupancy": "owner_primary",
        "coverage": {"dwelling_amount": 400000, "deductible": 1000},
    },
    "Missing roof age (pause)": {
        "quote_id": "DEMO-MISSING",
        "applicant_name": "Jordan Lee",
        "state": "TX",
        "zip_code": "75002",
        "year_built": 2008,
        "construction_type": "frame",
        "roof_type": "asphalt_shingle",
        "square_feet": 1800,
        "occupancy": "owner_primary",
        "coverage": {"dwelling_amount": 320000, "deductible": 1000},
    },
    "Wildfire mitigation follow-up": {
        "quote_id": "DEMO-WILDFIRE",
        "applicant_name": "Sam Carter",
        "state": "CA",
        "zip_code": "95014",
        "year_built": 2012,
        "construction_type": "frame",
        "roof_type": "asphalt_shingle",
        "roof_age_years": 7,
        "square_feet": 2000,
        "occupancy": "owner_primary",
        "coverage": {"dwelling_amount": 650000, "deductible": 2500},
    },
    "Decline (vacant)": {
        "quote_id": "DEMO-DECLINE",
        "applicant_name": "Pat Morgan",
        "state": "TX",
        "zip_code": "75003",
        "year_built": 1995,
        "construction_type": "frame",
        "roof_type": "asphalt_shingle",
        "roof_age_years": 10,
        "square_feet": 1600,
        "occupancy": "vacant",
        "coverage": {"dwelling_amount": 250000, "deductible": 1000},
    },
}


def api_post(path: str, payload: dict) -> dict:
    resp = httpx.post(f"{API_BASE}{path}", json=payload, timeout=60)
    return resp.json()


def api_get(path: str) -> dict:
    resp = httpx.get(f"{API_BASE}{path}", timeout=60)
    return resp.json()


def poll_run(run_id: str, attempts: int = 30) -> dict:
    for _ in range(attempts):
        data = api_get(f"/runs/{run_id}")
        status = (data.get("run") or {}).get("status")
        if status in {"completed", "pending_review", "waiting_for_info", "failed"}:
            return data
        time.sleep(0.4)
    return api_get(f"/runs/{run_id}")


def render_packet(packet: dict) -> None:
    if not packet:
        st.info("No decision packet yet.")
        return
    rec = packet.get("recommendation", "?")
    color = {"ACCEPT": "green", "REFER": "orange", "DECLINE": "red"}.get(rec, "gray")
    st.markdown(f"### Recommendation: :{color}[{rec}]")
    cols = st.columns(3)
    cols[0].metric("Confidence", f"{packet.get('confidence', 0):.0%}")
    cols[1].metric("Premium indication", f"${packet.get('premium_indication') or 0:,.0f}")
    cols[2].metric("Review status", packet.get("review_status", "-"))

    st.subheader("Reason codes")
    for rc in packet.get("reason_codes", []):
        st.write(f"- **{rc.get('code')}** ({rc.get('severity')}): {rc.get('description')}")

    st.subheader("Citations")
    for c in packet.get("citations", []):
        with st.expander(f"{c.get('chunk_id')} — {c.get('source')}"):
            st.caption(c.get("section", ""))
            st.write(c.get("text", ""))

    st.subheader("Next steps")
    for step in packet.get("next_steps", []):
        st.write(f"- {step}")


def page_submit() -> None:
    st.header("Submit Quote")
    choice = st.selectbox("Demo scenario", list(DEMO_SCENARIOS.keys()))
    payload_text = st.text_area(
        "Submission JSON",
        value=json.dumps(DEMO_SCENARIOS[choice], indent=2),
        height=320,
    )
    if st.button("Run underwriting", type="primary"):
        try:
            payload = json.loads(payload_text)
        except json.JSONDecodeError as exc:
            st.error(f"Invalid JSON: {exc}")
            return
        endpoint = "/quote/ho3" if "coverage" in payload else "/quote/run"
        started = api_post(endpoint, payload)
        run_id = started.get("run_id")
        if not run_id:
            st.error(started)
            return
        st.session_state["last_run_id"] = run_id
        st.success(f"Run started: {run_id}")
        data = poll_run(run_id)
        run = data.get("run") or {}
        st.write(f"**Status:** {run.get('status')}")
        if run.get("status") == "waiting_for_info":
            st.warning("Missing information — see the Answer Questions page.")
            st.json(data.get("required_questions"))
        else:
            render_packet(data.get("decision_packet"))


def page_answer() -> None:
    st.header("Answer Questions")
    run_id = st.text_input("Run ID", value=st.session_state.get("last_run_id", ""))
    if not run_id:
        return
    data = api_get(f"/runs/{run_id}")
    questions = data.get("required_questions") or []
    if not questions:
        st.info("This run has no pending questions.")
        return
    answers = {}
    for q in questions:
        field = q["field"]
        if q.get("type") == "boolean":
            answers[field] = st.checkbox(q["question"], key=f"a_{field}")
        else:
            answers[field] = st.text_input(q["question"], key=f"a_{field}")
    if st.button("Submit answers", type="primary"):
        result = api_post(f"/runs/{run_id}/answers", {"answers": answers})
        st.write(result)
        refreshed = poll_run(run_id)
        render_packet(refreshed.get("decision_packet"))


def page_reviews() -> None:
    st.header("Review Queue")
    pending = api_get("/reviews/pending").get("reviews", [])
    if not pending:
        st.info("No pending reviews.")
        return
    for task in pending:
        run_id = task["run_id"]
        with st.expander(f"{run_id} — {task['trigger']} ({task['priority']})"):
            st.json(task.get("review_packet", {}))
            cols = st.columns(4)
            for i, action in enumerate(["approve", "reject", "request_info", "close"]):
                if cols[i].button(action, key=f"{run_id}_{action}"):
                    res = api_post(
                        f"/reviews/{run_id}/actions",
                        {"action": action, "note": "via UI"},
                    )
                    st.write(res)


def page_audit() -> None:
    st.header("Audit Trail")
    run_id = st.text_input("Run ID", value=st.session_state.get("last_run_id", ""))
    if not run_id:
        return
    data = api_get(f"/runs/{run_id}/audit")
    for event in data.get("events", []):
        st.write(
            f"**{event.get('node')}** · {event.get('event_type')} · "
            f"{event.get('created_at')}"
        )
        if event.get("payload"):
            st.caption(json.dumps(event["payload"]))


def main() -> None:
    st.set_page_config(page_title="QuoteCopilot", page_icon="🏠", layout="wide")
    st.title("QuoteCopilot — HO3 Underwriting Review")
    st.caption(f"API: {API_BASE}  •  Synthetic data and synthetic guidelines.")
    page = st.sidebar.radio(
        "Pages",
        ["Submit Quote", "Answer Questions", "Review Queue", "Audit Trail"],
    )
    if page == "Submit Quote":
        page_submit()
    elif page == "Answer Questions":
        page_answer()
    elif page == "Review Queue":
        page_reviews()
    else:
        page_audit()


if __name__ == "__main__":
    main()
