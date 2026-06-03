from typing import Optional

import streamlit as st

from services.task_service import CATEGORIES


def render_sidebar() -> Optional[str]:
    with st.sidebar:
        st.markdown('<p class="sidebar-label">Filter by Category</p>', unsafe_allow_html=True)
        st.caption("Applies to the Tasks tab only.")

        options = ["All"] + CATEGORIES
        selected: str = st.radio(
            label="category_radio",
            options=options,
            index=0,
            label_visibility="collapsed",
            key="category_filter",
        )

        st.divider()

        st.markdown('<p class="sidebar-label">Priority Guide</p>', unsafe_allow_html=True)
        st.markdown(
            """
            <div style="display:flex;flex-direction:column;gap:8px;padding:4px 0">
                <div><span class="badge badge-high">High</span>
                     <span style="font-size:0.78rem;color:#6b7280;margin-left:6px">Urgent</span></div>
                <div><span class="badge badge-medium">Medium</span>
                     <span style="font-size:0.78rem;color:#6b7280;margin-left:6px">Normal</span></div>
                <div><span class="badge badge-low">Low</span>
                     <span style="font-size:0.78rem;color:#6b7280;margin-left:6px">Whenever</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return selected
