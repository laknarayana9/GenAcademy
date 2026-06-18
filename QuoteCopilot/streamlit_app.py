"""QuoteCopilot Streamlit UI — entrypoint.

A pure rendering + httpx client layer over the FastAPI backend. This module only
bootstraps the theme and routes between the two personas; all logic lives in the
``ui`` package (``ui.pages.applicant`` and ``ui.pages.underwriter``).
"""

from __future__ import annotations

import streamlit as st

from ui import api_client, components
from ui.pages import applicant, underwriter

PERSONAS = {
    "Applicant": ("🧑 Get a quote", applicant.render),
    "Underwriter": ("🛡️ Review console", underwriter.render),
}


def main() -> None:
    st.set_page_config(page_title="QuoteCopilot", page_icon="🏠", layout="wide")
    components.inject_styles()
    components.header()

    with st.sidebar:
        st.markdown("### I am a…")
        persona = st.radio(
            "persona",
            list(PERSONAS.keys()),
            format_func=lambda k: PERSONAS[k][0],
            label_visibility="collapsed",
        )
        st.divider()
        if api_client.health():
            st.success(f"API online · {api_client.API_BASE}")
        else:
            st.error(
                f"API unreachable at {api_client.API_BASE}.\n\n"
                "Start it with:\n`uvicorn app.api.main:app`"
            )
        st.caption("Synthetic data & guidelines. Decisions are illustrative.")

    PERSONAS[persona][1]()


if __name__ == "__main__":
    main()
