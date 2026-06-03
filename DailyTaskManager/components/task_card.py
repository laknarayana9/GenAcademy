import html as _html
from datetime import datetime

import streamlit as st

from models.task import Task
from services.task_service import TaskService
from utils.persistence import PersistenceError

_PRIORITY_BADGE: dict = {
    "High":   '<span class="badge badge-high">High</span>',
    "Medium": '<span class="badge badge-medium">Medium</span>',
    "Low":    '<span class="badge badge-low">Low</span>',
}


def _fmt_time(time_str: str) -> str:
    try:
        return datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return time_str


def render_task_card(task: Task, service: TaskService) -> None:
    badge_html = _PRIORITY_BADGE.get(task.priority, "")
    cat_html = f'<span class="cat-chip">{_html.escape(task.category)}</span>'
    time_html = (
        f'<span class="due-time">⏱ {_fmt_time(task.due_time)}</span>'
        if task.due_time
        else ""
    )

    title_class = "task-title-done" if task.status == "completed" else "task-title"
    title_html = f'<span class="{title_class}">{_html.escape(task.title)}</span>'

    col_info, col_done, col_del = st.columns([6, 0.6, 0.6])

    with col_info:
        st.markdown(
            f"""
            <div class="task-row">
                {badge_html}
                {title_html}
                {cat_html}
                {time_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_done:
        if task.status == "pending":
            if st.button("✓", key=f"c_{task.id}", help="Mark complete", use_container_width=True):
                try:
                    service.complete(task.id)
                    st.rerun()
                except PersistenceError as exc:
                    st.error(f"Could not save: {exc}")

    with col_del:
        if st.button("✕", key=f"d_{task.id}", help="Delete task", use_container_width=True):
            try:
                service.delete(task.id)
                st.rerun()
            except PersistenceError as exc:
                st.error(f"Could not save: {exc}")

    st.markdown('<div class="task-divider"></div>', unsafe_allow_html=True)
