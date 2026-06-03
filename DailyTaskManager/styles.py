import streamlit as st

# ── All visual styles live here ────────────────────────────────────────────────
# Edit this block to change colors, spacing, typography, badges, or card style.

CSS = """
<style>
/* ── Base & background ──────────────────────────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #f8fafc;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
    color: #1f2937;
}

[data-testid="stSidebar"] {
    background-color: #ffffff;
    border-right: 1px solid #e5e7eb;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 2rem;
}

/* Remove default Streamlit top padding */
[data-testid="stAppViewContainer"] > section > div {
    padding-top: 1.5rem;
}

/* ── Top bar ────────────────────────────────────────────────────────────────── */
.top-bar-date {
    font-size: 1.45rem;
    font-weight: 700;
    color: #111827;
    margin: 0 0 2px 0;
    line-height: 1.2;
}

.top-bar-sub {
    font-size: 0.82rem;
    color: #9ca3af;
    margin: 0;
    letter-spacing: 0.03em;
}

/* ── Section headers ────────────────────────────────────────────────────────── */
.section-header {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 20px 0 10px 0;
    padding: 0;
}

/* ── Task row layout ────────────────────────────────────────────────────────── */
.task-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 4px;
    flex-wrap: wrap;
    min-height: 42px;
}

.task-title {
    font-size: 0.93rem;
    font-weight: 500;
    color: #111827;
    flex: 1;
    min-width: 100px;
}

.task-title-done {
    font-size: 0.93rem;
    font-weight: 400;
    color: #9ca3af;
    text-decoration: line-through;
    flex: 1;
    min-width: 100px;
}

.due-time {
    font-size: 0.78rem;
    color: #6b7280;
    white-space: nowrap;
    background: #f9fafb;
    padding: 2px 6px;
    border-radius: 4px;
    border: 1px solid #e5e7eb;
}

/* ── Priority badges ────────────────────────────────────────────────────────── */
.badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 9999px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    white-space: nowrap;
    flex-shrink: 0;
}

.badge-high   { background: #fee2e2; color: #b91c1c; }
.badge-medium { background: #fef3c7; color: #b45309; }
.badge-low    { background: #f1f5f9; color: #64748b; }

/* ── Category chips ─────────────────────────────────────────────────────────── */
.cat-chip {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 5px;
    background: #f3f4f6;
    color: #4b5563;
    font-size: 0.72rem;
    font-weight: 500;
    white-space: nowrap;
    border: 1px solid #e5e7eb;
    flex-shrink: 0;
}

/* ── Task row divider ───────────────────────────────────────────────────────── */
.task-divider {
    border: none;
    border-top: 1px solid #f3f4f6;
    margin: 0;
}

/* ── Empty state ────────────────────────────────────────────────────────────── */
.empty-state {
    text-align: center;
    color: #d1d5db;
    padding: 36px 0;
    font-size: 0.88rem;
    letter-spacing: 0.02em;
}

/* ── Sidebar labels ─────────────────────────────────────────────────────────── */
.sidebar-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #9ca3af;
    margin: 0 0 10px 0;
}

/* ── Action buttons: make them compact and subtle ───────────────────────────── */
button[data-testid="baseButton-secondary"] {
    font-size: 0.78rem;
    padding: 4px 6px !important;
    min-height: 32px;
    background-color: #f9fafb;
    border: 1px solid #e5e7eb;
    color: #6b7280;
}

button[data-testid="baseButton-secondary"]:hover {
    background-color: #f3f4f6;
    border-color: #d1d5db;
    color: #374151;
}

/* ── Tab bar ──────────────────────────────────────────────────────────────── */
[data-testid="stTabs"] button[role="tab"] {
    font-size: 0.88rem;
    font-weight: 500;
    color: #6b7280;
    padding: 6px 16px;
}

[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    color: #111827;
    font-weight: 600;
}

/* ── Metric cards ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 16px 20px;
}

[data-testid="stMetricLabel"] p {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #9ca3af;
}

[data-testid="stMetricValue"] {
    font-size: 1.55rem;
    font-weight: 700;
    color: #111827;
}
</style>
"""


def inject_styles() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
