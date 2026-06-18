"""Applicant / agent journey.

A guided multi-step quote wizard (no JSON), a live agent-pipeline reveal, inline
follow-up questions when the run pauses, and a polished decision result card.
State is held in ``st.session_state`` so the flow advances automatically.
"""

from __future__ import annotations

import streamlit as st

from ui import api_client, components
from ui.labels import (
    CONSTRUCTION_OPTIONS,
    OCCUPANCY_OPTIONS,
    ROOF_OPTIONS,
    US_STATES,
)

DEMO_PREFILLS = {
    "— start blank —": {},
    "Clean home (likely approve)": {
        "applicant_name": "Alex Rivera", "state": "TX", "zip_code": "75001",
        "year_built": 2015, "construction": "Masonry (brick/block)", "roof": "Metal",
        "roof_age_years": 4, "square_feet": 2200,
        "occupancy": "Owner — primary residence",
        "dwelling_amount": 400000, "deductible": 1000,
    },
    "Older roof (referral)": {
        "applicant_name": "Casey Kim", "state": "TX", "zip_code": "75001",
        "year_built": 1998, "construction": "Wood frame", "roof": "Asphalt shingle",
        "roof_age_years": 25, "square_feet": 2000,
        "occupancy": "Owner — primary residence",
        "dwelling_amount": 350000, "deductible": 1000,
    },
    "California wildfire (follow-up)": {
        "applicant_name": "Sam Carter", "state": "CA", "zip_code": "95014",
        "year_built": 2012, "construction": "Wood frame", "roof": "Asphalt shingle",
        "roof_age_years": 7, "square_feet": 2000,
        "occupancy": "Owner — primary residence",
        "dwelling_amount": 650000, "deductible": 2500,
    },
    "Vacant home (decline)": {
        "applicant_name": "Pat Morgan", "state": "TX", "zip_code": "75003",
        "year_built": 1995, "construction": "Wood frame", "roof": "Asphalt shingle",
        "roof_age_years": 10, "square_feet": 1600, "occupancy": "Vacant",
        "dwelling_amount": 250000, "deductible": 1000,
    },
}


def _reset() -> None:
    for key in list(st.session_state.keys()):
        if key.startswith("app_"):
            del st.session_state[key]


def _init() -> None:
    st.session_state.setdefault("app_phase", "form")
    st.session_state.setdefault("app_run_id", None)


def render() -> None:
    _init()
    phase = st.session_state["app_phase"]
    if phase == "form":
        _render_form()
    else:
        _render_result()


# --- form ------------------------------------------------------------------
def _render_form() -> None:
    st.subheader("Get a homeowner insurance quote")
    demo = st.selectbox(
        "Quick-fill a demo scenario (optional)", list(DEMO_PREFILLS.keys())
    )
    p = DEMO_PREFILLS[demo]

    with st.form("quote_form"):
        st.markdown("##### Applicant & property")
        c1, c2 = st.columns(2)
        applicant_name = c1.text_input("Applicant name", value=p.get("applicant_name", ""))
        state = c2.selectbox(
            "State", US_STATES,
            index=US_STATES.index(p["state"]) if p.get("state") in US_STATES else 43,
        )
        c3, c4, c5 = st.columns(3)
        zip_code = c3.text_input("ZIP code", value=p.get("zip_code", ""))
        year_built = c4.number_input(
            "Year built", min_value=1850, max_value=2026,
            value=int(p.get("year_built", 2010)),
        )
        square_feet = c5.number_input(
            "Square feet", min_value=200, max_value=20000,
            value=int(p.get("square_feet", 2000)), step=50,
        )
        c6, c7, c8 = st.columns(3)
        construction = c6.selectbox(
            "Construction", list(CONSTRUCTION_OPTIONS.keys()),
            index=_opt_index(CONSTRUCTION_OPTIONS, p.get("construction")),
        )
        roof = c7.selectbox(
            "Roof type", list(ROOF_OPTIONS.keys()),
            index=_opt_index(ROOF_OPTIONS, p.get("roof")),
        )
        roof_known = c8.checkbox("Roof age known?", value="roof_age_years" in p)
        roof_age = st.slider(
            "Roof age (years)", 0, 50, int(p.get("roof_age_years", 10)),
            disabled=not roof_known,
        )

        st.markdown("##### Coverage & occupancy")
        c9, c10, c11 = st.columns(3)
        dwelling = c9.number_input(
            "Dwelling coverage (A)", min_value=10000, max_value=5000000,
            value=int(p.get("dwelling_amount", 350000)), step=10000,
        )
        deductible = c10.number_input(
            "Deductible", min_value=0, max_value=50000,
            value=int(p.get("deductible", 1000)), step=250,
        )
        occupancy = c11.selectbox(
            "Occupancy", list(OCCUPANCY_OPTIONS.keys()),
            index=_opt_index(OCCUPANCY_OPTIONS, p.get("occupancy"), default=0),
        )

        st.markdown("##### Hazard context (optional)")
        c12, c13 = st.columns(2)
        coast = c12.number_input(
            "Distance to coast (miles, 0 = unknown)", min_value=0.0,
            max_value=500.0, value=0.0, step=0.5,
        )
        mitigation = c13.selectbox(
            "Wildfire mitigation", ["Unknown", "Yes", "No"], index=0
        )

        submitted = st.form_submit_button("Get my decision", type="primary")

    if submitted:
        if not applicant_name or not zip_code or len(zip_code) != 5 or not zip_code.isdigit():
            st.error("Please enter a name and a valid 5-digit ZIP code.")
            return
        submission = {
            "quote_id": f"ui-{zip_code}-{year_built}",
            "applicant_name": applicant_name,
            "state": state,
            "zip_code": zip_code,
            "year_built": int(year_built),
            "construction_type": CONSTRUCTION_OPTIONS[construction],
            "roof_type": ROOF_OPTIONS[roof],
            "square_feet": int(square_feet),
            "occupancy": OCCUPANCY_OPTIONS[occupancy],
            "coverage": {"dwelling_amount": float(dwelling), "deductible": float(deductible)},
        }
        if roof_known:
            submission["roof_age_years"] = int(roof_age)
        if coast > 0:
            submission["distance_to_coast_miles"] = float(coast)
        if mitigation != "Unknown":
            submission["wildfire_mitigation"] = mitigation == "Yes"

        _submit(submission)


def _submit(submission: dict) -> None:
    try:
        with st.spinner("Running underwriting agents..."):
            started = api_client.start_ho3(submission)
            run_id = started["run_id"]
            api_client.poll_run(run_id)
    except api_client.ApiError as exc:
        st.error(f"Could not start the quote: {exc}")
        return
    st.session_state["app_run_id"] = run_id
    st.session_state["app_phase"] = "result"
    st.rerun()


# --- result ----------------------------------------------------------------
def _render_result() -> None:
    run_id = st.session_state["app_run_id"]
    detail = api_client.get_run(run_id)
    run = detail.get("run") or {}
    status = run.get("status")

    top = st.columns([3, 1])
    top[0].markdown(f"**Quote** `{run_id}`")
    if top[1].button("New quote"):
        _reset()
        st.rerun()

    if status == "waiting_for_info":
        _render_followup(run_id, detail)
        return

    if status == "failed":
        st.error("This submission could not be processed. Please start a new quote.")
        return

    packet = detail.get("decision_packet") or {}
    components.decision_banner(packet)
    st.write("")
    components.decision_metrics(packet)
    st.divider()

    left, right = st.columns([3, 2])
    with left:
        components.reason_codes(packet)
        st.write("")
        components.next_steps(packet)
        st.write("")
        components.citations(packet)
    with right:
        with st.container(border=True):
            components.pipeline_timeline(api_client.get_audit(run_id))

    if status == "pending_review":
        st.info(
            "This quote needs a quick review by an underwriter before it is final. "
            "Track it in the **Underwriter** console."
        )


def _render_followup(run_id: str, detail: dict) -> None:
    st.warning("We need a little more information to finish your quote.")
    questions = detail.get("required_questions") or []
    with st.form("followup_form"):
        answers = {}
        for q in questions:
            field = q["field"]
            label = q.get("question", field)
            qtype = q.get("type", "text")
            if qtype == "boolean":
                answers[field] = st.checkbox(label, key=f"app_q_{field}")
            elif field == "coverage":
                st.markdown(f"**{label}**")
                cc = st.columns(2)
                answers["coverage"] = {
                    "dwelling_amount": cc[0].number_input(
                        "Dwelling amount", min_value=10000, value=350000, step=10000,
                        key="app_q_dwelling",
                    ),
                    "deductible": cc[1].number_input(
                        "Deductible", min_value=0, value=1000, step=250,
                        key="app_q_deductible",
                    ),
                }
            elif field in {"roof_age_years", "year_built", "square_feet"}:
                answers[field] = st.number_input(
                    label, min_value=0, value=0, step=1, key=f"app_q_{field}"
                )
            else:
                answers[field] = st.text_input(label, key=f"app_q_{field}")
        submitted = st.form_submit_button("Submit information", type="primary")

    if submitted:
        with st.spinner("Updating your quote..."):
            api_client.submit_answers(run_id, answers)
            api_client.poll_run(run_id)
        st.rerun()


def _opt_index(options: dict, label: str | None, default: int = 0) -> int:
    keys = list(options.keys())
    if label in keys:
        return keys.index(label)
    return default
