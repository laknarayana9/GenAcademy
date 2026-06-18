"""Reusable Streamlit presentation components.

Cards, badges, the agent pipeline timeline, and citation rendering. These are
pure rendering helpers driven by API payloads.
"""

from __future__ import annotations

import streamlit as st

from ui.labels import (
    NODE_LABEL,
    PIPELINE_STEPS,
    PRIORITY_STYLE,
    RECOMMENDATION_STYLE,
    SEVERITY_STYLE,
    STATUS_STYLE,
    TRIGGER_LABEL,
)


def inject_styles() -> None:
    """Inject lightweight CSS used across pages."""
    st.markdown(
        """
        <style>
        .qc-badge {display:inline-block;padding:2px 10px;border-radius:999px;
            color:#fff;font-size:0.78rem;font-weight:600;letter-spacing:.02em;}
        .qc-chip {display:inline-block;padding:3px 10px;margin:3px 4px 3px 0;
            border-radius:8px;font-size:0.8rem;border:1px solid #e2e8f0;
            background:#f8fafc;}
        .qc-card {border:1px solid #e2e8f0;border-radius:14px;padding:22px 24px;
            background:#ffffff;box-shadow:0 1px 3px rgba(15,23,42,.06);}
        .qc-decision {border-radius:16px;padding:24px 28px;color:#fff;}
        .qc-decision h2 {color:#fff;margin:0;font-size:1.6rem;}
        .qc-decision p {color:#fff;opacity:.92;margin:4px 0 0;}
        .qc-step {padding:6px 0;border-left:2px solid #e2e8f0;padding-left:14px;
            margin-left:6px;}
        .qc-step.done {border-color:#16a34a;}
        .qc-muted {color:#64748b;font-size:0.85rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def header() -> None:
    st.markdown(
        "<h1 style='margin-bottom:0'>🏠 QuoteCopilot</h1>"
        "<p class='qc-muted'>AI-assisted HO3 homeowner underwriting "
        "&middot; synthetic data &amp; guidelines</p>",
        unsafe_allow_html=True,
    )


def badge(text: str, color: str) -> str:
    return f"<span class='qc-badge' style='background:{color}'>{text}</span>"


def status_badge(status: str) -> str:
    style = STATUS_STYLE.get(status, {"color": "#64748b", "label": status})
    return badge(style["label"], style["color"])


def priority_badge(priority: str) -> str:
    style = PRIORITY_STYLE.get(priority, {"color": "#64748b", "label": priority})
    return badge(style["label"], style["color"])


def decision_banner(packet: dict) -> None:
    """Big colored decision headline."""
    rec = packet.get("recommendation", "REFER")
    style = RECOMMENDATION_STYLE.get(rec, RECOMMENDATION_STYLE["REFER"])
    st.markdown(
        f"""
        <div class='qc-decision' style='background:{style["color"]}'>
            <h2>{style["emoji"]} {style["headline"]}</h2>
            <p>Recommendation: <strong>{rec}</strong></p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def decision_metrics(packet: dict) -> None:
    cols = st.columns(3)
    cols[0].metric("Confidence", f"{packet.get('confidence', 0):.0%}")
    premium = packet.get("premium_indication")
    cols[1].metric(
        "Annual premium", f"${premium:,.0f}" if premium else "—"
    )
    cols[2].metric("Review status", packet.get("review_status", "—").replace("_", " "))


def reason_codes(packet: dict) -> None:
    findings = packet.get("reason_codes", [])
    if not findings:
        return
    st.markdown("**Why this decision**")
    chips = ""
    for rc in findings:
        color = SEVERITY_STYLE.get(rc.get("severity", "info"), "#64748b")
        chips += (
            f"<span class='qc-chip' style='border-color:{color}'>"
            f"<strong style='color:{color}'>{rc.get('code')}</strong> "
            f"&middot; {rc.get('description', '')}</span>"
        )
    st.markdown(chips, unsafe_allow_html=True)


def citations(packet: dict) -> None:
    cites = packet.get("citations", [])
    if not cites:
        return
    st.markdown("**Guideline citations**")
    for c in cites:
        title = f"{c.get('source', 'guideline')} — {c.get('section', c.get('chunk_id'))}"
        with st.expander(title):
            st.caption(f"chunk: {c.get('chunk_id')}")
            st.write(c.get("text", ""))


def next_steps(packet: dict) -> None:
    steps = packet.get("next_steps", [])
    if not steps:
        return
    st.markdown("**Next steps**")
    for step in steps:
        st.markdown(f"- {step}")


def pipeline_timeline(events: list[dict]) -> None:
    """Render the agent pipeline as a vertical timeline from audit events."""
    completed_nodes = {
        e.get("node")
        for e in events
        if e.get("event_type") in {"completed", "paused", "resolved"}
    }
    st.markdown("**What the agents did**")
    for node, label in PIPELINE_STEPS:
        if node not in {e.get("node") for e in events}:
            continue
        done = node in completed_nodes
        mark = "✅" if done else "⏳"
        st.markdown(
            f"<div class='qc-step {'done' if done else ''}'>{mark} {label}</div>",
            unsafe_allow_html=True,
        )


def submission_summary(canonical: dict) -> None:
    """Compact read-only summary of a canonical submission."""
    if not canonical:
        st.info("No submission detail available.")
        return
    cov = canonical.get("coverage", {}) or {}
    rows = {
        "Applicant": canonical.get("applicant_name"),
        "Location": f"{canonical.get('state')} {canonical.get('zip_code')}",
        "Year built": canonical.get("year_built"),
        "Construction": canonical.get("construction_type"),
        "Roof": f"{canonical.get('roof_type')} ({canonical.get('roof_age_years')} yrs)",
        "Square feet": canonical.get("square_feet"),
        "Occupancy": canonical.get("occupancy"),
        "Dwelling / deductible": f"${cov.get('dwelling_amount', 0):,.0f}"
        f" / ${cov.get('deductible', 0):,.0f}",
    }
    for k, v in rows.items():
        st.markdown(f"<span class='qc-muted'>{k}:</span> **{v}**", unsafe_allow_html=True)


def trigger_label(trigger: str) -> str:
    return TRIGGER_LABEL.get(trigger, trigger)
