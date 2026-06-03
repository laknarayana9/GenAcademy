from typing import Optional

import altair as alt
import pandas as pd
import streamlit as st

from services.task_service import TaskService, PRIORITIES, CATEGORIES

_PRIORITY_COLORS = {
    "High":   "#ef4444",
    "Medium": "#f59e0b",
    "Low":    "#22c55e",
}

_CATEGORY_COLORS = {
    "Work":     "#3b82f6",
    "Personal": "#a855f7",
    "Errands":  "#14b8a6",
    "Learning": "#8b5cf6",
    "Health":   "#22c55e",
}

_STATUS_COLORS = {
    "Pending":   "#f97316",
    "Completed": "#22c55e",
}


def _bar_chart(df: pd.DataFrame, x_col: str, y_col: str, color_map: dict) -> alt.Chart:
    domain = list(color_map.keys())
    color_range = list(color_map.values())
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                f"{x_col}:N",
                sort=domain,
                axis=alt.Axis(labelAngle=0, title=None, labelFontSize=12),
            ),
            y=alt.Y(
                f"{y_col}:Q",
                axis=alt.Axis(title=y_col, tickMinStep=1, labelFontSize=11),
            ),
            color=alt.Color(
                f"{x_col}:N",
                scale=alt.Scale(domain=domain, range=color_range),
                legend=None,
            ),
            tooltip=[
                alt.Tooltip(f"{x_col}:N", title=x_col),
                alt.Tooltip(f"{y_col}:Q", title=y_col),
            ],
        )
        .properties(height=240)
    )


def render_insights(service: TaskService, category_filter: Optional[str] = None) -> None:
    all_tasks = service.get_all()

    if category_filter and category_filter != "All":
        all_tasks = [t for t in all_tasks if t.category == category_filter]

    if not all_tasks:
        label = f"'{category_filter}'" if category_filter and category_filter != "All" else "any category"
        st.markdown(
            f'<div class="empty-state">No tasks found for {label} · Add tasks in the Tasks tab to see insights</div>',
            unsafe_allow_html=True,
        )
        return

    total = len(all_tasks)
    completed = sum(1 for t in all_tasks if t.status == "completed")
    pending = total - completed
    rate = round(completed / total * 100, 1) if total else 0.0

    # ── Metric cards ──────────────────────────────────────────────────────────
    st.markdown('<p class="section-header">Overview</p>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tasks", total)
    c2.metric("Completed", completed)
    c3.metric("Pending", pending)
    c4.metric("Completion Rate", f"{rate}%")

    st.divider()

    # ── Charts row 1: Priority & Category ────────────────────────────────────
    st.markdown('<p class="section-header">Breakdown</p>', unsafe_allow_html=True)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown("**Tasks by Priority**")
        priority_counts = {p: 0 for p in PRIORITIES}
        for t in all_tasks:
            if t.priority in priority_counts:
                priority_counts[t.priority] += 1
        p_df = pd.DataFrame({
            "Priority": list(priority_counts.keys()),
            "Tasks": list(priority_counts.values()),
        })
        st.altair_chart(_bar_chart(p_df, "Priority", "Tasks", _PRIORITY_COLORS), use_container_width=True)

    with col_r:
        st.markdown("**Tasks by Category**")
        cat_counts = {c: 0 for c in CATEGORIES}
        for t in all_tasks:
            if t.category in cat_counts:
                cat_counts[t.category] += 1
        c_df = pd.DataFrame({
            "Category": list(cat_counts.keys()),
            "Tasks": list(cat_counts.values()),
        })
        st.altair_chart(_bar_chart(c_df, "Category", "Tasks", _CATEGORY_COLORS), use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row 2: Status & Summary table ─────────────────────────────────
    col_status, col_table = st.columns(2)

    with col_status:
        st.markdown("**Pending vs Completed**")
        status_df = pd.DataFrame({
            "Status": ["Pending", "Completed"],
            "Tasks": [pending, completed],
        })
        st.altair_chart(_bar_chart(status_df, "Status", "Tasks", _STATUS_COLORS), use_container_width=True)

    with col_table:
        st.markdown("**Summary by Priority**")
        rows = []
        for p in PRIORITIES:
            p_tasks = [t for t in all_tasks if t.priority == p]
            done = sum(1 for t in p_tasks if t.status == "completed")
            rows.append({
                "Priority": p,
                "Total": len(p_tasks),
                "Pending": len(p_tasks) - done,
                "Completed": done,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
