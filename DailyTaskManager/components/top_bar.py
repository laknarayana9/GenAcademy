from datetime import datetime

import streamlit as st

from services.task_service import TaskService, CATEGORIES, PRIORITIES
from utils.persistence import PersistenceError


def render_top_bar(service: TaskService) -> None:
    today = datetime.now()
    day_str = f"{today.strftime('%A, %B')} {today.day}, {today.year}"

    col_date, col_btn = st.columns([3, 1])

    with col_date:
        st.markdown(f'<p class="top-bar-date">{day_str}</p>', unsafe_allow_html=True)
        st.markdown('<p class="top-bar-sub">Daily Task Manager</p>', unsafe_allow_html=True)

    with col_btn:
        if st.button("＋ Add Task", use_container_width=True, type="primary"):
            st.session_state["show_add_form"] = not st.session_state.get("show_add_form", False)

    if st.session_state.get("show_add_form", False):
        _render_add_form(service)

    st.divider()


def _render_add_form(service: TaskService) -> None:
    with st.form("add_task_form", clear_on_submit=True):
        st.markdown("**New Task**")
        title = st.text_input("Task title", placeholder="What needs to be done?", label_visibility="collapsed")

        col1, col2, col3 = st.columns(3)
        with col1:
            priority = st.selectbox("Priority", PRIORITIES, index=1)
        with col2:
            category = st.selectbox("Category", CATEGORIES)
        with col3:
            add_time = st.checkbox("Set due time", value=False)
            due_time_input = st.time_input("Due time", label_visibility="collapsed")

        col_sub, col_cancel = st.columns(2)
        with col_sub:
            submitted = st.form_submit_button("Add Task", use_container_width=True, type="primary")
        with col_cancel:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)

        if submitted:
            if title.strip():
                due_str = due_time_input.strftime("%H:%M") if add_time else None
                try:
                    service.add(title, priority, category, due_str)
                    st.session_state["show_add_form"] = False
                    st.rerun()
                except PersistenceError as exc:
                    st.error(f"Could not save task: {exc}")
            else:
                st.warning("Please enter a task title.")

        if cancelled:
            st.session_state["show_add_form"] = False
            st.rerun()
