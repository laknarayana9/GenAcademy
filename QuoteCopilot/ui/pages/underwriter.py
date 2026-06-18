"""Underwriter review console.

Pending review queue, full packet inspection, reviewer actions
(approve / reject / request_info / close), and a run audit trail.
"""

from __future__ import annotations

import streamlit as st

from ui import api_client, components

ACTIONS = {
    "Approve": ("approve", "primary"),
    "Reject": ("reject", "secondary"),
    "Request info": ("request_info", "secondary"),
    "Close": ("close", "secondary"),
}


def render() -> None:
    st.subheader("Underwriter review console")
    tab_queue, tab_audit = st.tabs(["Review queue", "Audit trail"])
    with tab_queue:
        _render_queue()
    with tab_audit:
        _render_audit()


def _render_queue() -> None:
    pending = api_client.pending_reviews()
    cols = st.columns([1, 3])
    cols[0].metric("Open reviews", len(pending))
    if cols[1].button("Refresh"):
        st.rerun()

    if not pending:
        st.success("No pending reviews. The queue is clear.")
        return

    options = {
        f"{t['run_id'][:8]} · {components.trigger_label(t['trigger'])} ({t['priority']})": t
        for t in pending
    }
    choice = st.selectbox("Select a review task", list(options.keys()))
    task = options[choice]
    _render_task(task)


def _render_task(task: dict) -> None:
    run_id = task["run_id"]
    detail = api_client.get_review(run_id)
    packet = detail.get("decision_packet") or {}
    run = detail.get("run") or {}

    st.markdown(
        components.priority_badge(task.get("priority", "medium"))
        + " "
        + components.status_badge(run.get("status", "pending_review")),
        unsafe_allow_html=True,
    )

    review_packet = task.get("review_packet") or {}
    left, right = st.columns([2, 3])
    with left:
        with st.container(border=True):
            st.markdown("**Submission**")
            components.submission_summary(review_packet.get("submission") or {})
    with right:
        components.decision_banner(packet)
        st.write("")
        components.decision_metrics(packet)
        flags = (task.get("review_packet") or {}).get("review_flags", [])
        if flags:
            st.markdown("**Review flags**")
            st.markdown(
                " ".join(
                    f"<span class='qc-chip' style='border-color:#d97706'>{f}</span>"
                    for f in flags
                ),
                unsafe_allow_html=True,
            )

    st.divider()
    components.reason_codes(packet)
    st.write("")
    components.citations(packet)

    st.divider()
    _render_actions(run_id)


def _render_actions(run_id: str) -> None:
    st.markdown("**Resolve this review**")
    note = st.text_area("Reviewer note (optional)", key=f"note_{run_id}")
    cols = st.columns(len(ACTIONS))
    for i, (label, (action, kind)) in enumerate(ACTIONS.items()):
        if cols[i].button(label, key=f"{run_id}_{action}", type=kind):
            result = api_client.apply_action(run_id, action, note)
            st.success(
                f"Action '{label}' applied — run is now "
                f"'{result.get('status')}'."
            )
            st.rerun()


def _render_audit() -> None:
    runs = api_client.list_runs(limit=50)
    if not runs:
        st.info("No runs yet.")
        return
    labels = {
        f"{r['run_id'][:8]} · {r.get('status')} · {r.get('quote_id', '')}": r["run_id"]
        for r in runs
    }
    choice = st.selectbox("Select a run", list(labels.keys()))
    run_id = labels[choice]

    events = api_client.get_audit(run_id)
    if not events:
        st.info("No audit events for this run.")
        return
    for e in events:
        st.markdown(
            f"**{e.get('node')}** · `{e.get('event_type')}` "
            f"<span class='qc-muted'>{e.get('created_at', '')}</span>",
            unsafe_allow_html=True,
        )
        payload = e.get("payload")
        if payload:
            st.json(payload, expanded=False)
