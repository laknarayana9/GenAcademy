import streamlit as st

from styles import inject_styles
from services.task_service import TaskService
from components.top_bar import render_top_bar
from components.task_card import render_task_card
from components.sidebar import render_sidebar
from components.csv_handler import render_csv_handler
from components.insights import render_insights
from utils.persistence import pop_load_warning


def main() -> None:
    st.set_page_config(
        page_title="Daily Task Manager",
        page_icon="✓",
        layout="wide",
    )

    inject_styles()

    service = TaskService()

    category_filter = render_sidebar()

    tab1, tab2, tab3 = st.tabs(["  Tasks", "  Import / Export", "  Insights"])

    # ── Tab 1: Tasks ─────────────────────────────────────────────────────────
    with tab1:
        render_top_bar(service)

        pending, completed = service.get_sorted_filtered(category_filter)

        warn = pop_load_warning()
        if warn:
            st.warning(warn)

        st.markdown(
            f'<p class="section-header">Pending Tasks ({len(pending)})</p>',
            unsafe_allow_html=True,
        )

        if not pending:
            st.markdown(
                '<div class="empty-state">No pending tasks · Click "＋ Add Task" to get started</div>',
                unsafe_allow_html=True,
            )
        else:
            for task in pending:
                render_task_card(task, service)

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander(f"✓  Completed ({len(completed)})", expanded=False):
            if not completed:
                st.markdown(
                    '<div class="empty-state">No completed tasks yet</div>',
                    unsafe_allow_html=True,
                )
            else:
                for task in completed:
                    render_task_card(task, service)

    # ── Tab 2: Import / Export ────────────────────────────────────────────────
    with tab2:
        render_csv_handler(service)

    # ── Tab 3: Insights ───────────────────────────────────────────────────────
    with tab3:
        render_insights(service, category_filter)


main()
