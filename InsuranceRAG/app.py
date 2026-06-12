"""
app.py — Streamlit chat UI for the Insurance RAG pipeline.

A thin wrapper over the existing pipeline (no core logic changes): it calls
rag.answer() and surfaces the cited answer, the retrieved chunks with their
rerank scores, and the "I don't know" refusal state.

Run:
    streamlit run app.py

Requires the same .env as the CLI (OpenAI + Nebius + Pinecone) and an index
that has already been populated via `python ingest.py`.
"""

import streamlit as st
from dotenv import load_dotenv

from retriever import HybridRetriever
from reranker import LLMReranker, MIN_RELEVANCE_SCORE
from rag import answer

load_dotenv()

st.set_page_config(page_title="Home Insurance Agent Assistant", page_icon="🏠", layout="centered")


# ---------------------------------------------------------------------------
# Cached resources — built once per (namespace) and reused across reruns.
# ---------------------------------------------------------------------------

@st.cache_resource(show_spinner="Loading reranker...")
def get_reranker() -> LLMReranker:
    return LLMReranker()


@st.cache_resource(show_spinner="Building retriever (BM25 + Pinecone)...")
def get_retriever(namespace: str) -> HybridRetriever:
    return HybridRetriever(namespace=namespace)


# ---------------------------------------------------------------------------
# Sidebar — config
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("⚙️ Settings")
    namespace = st.radio(
        "Chunking strategy",
        options=["paragraph", "fixed"],
        help="Which Pinecone namespace / chunking strategy to query.",
    )
    use_rerank = st.toggle(
        "LLM reranking (Nebius)",
        value=True,
        help="Rerank the fused candidate pool and enable the relevance-based "
        "refusal path. Turn off to see raw RRF behavior.",
    )
    st.caption(
        f"Refusal threshold: top rerank score < {MIN_RELEVANCE_SCORE} → "
        '"I don\'t know". Only active when reranking is on.'
    )
    if st.button("Clear conversation"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.caption(
        "Sample questions:\n"
        "- Is knob-and-tube wiring eligible for HO3?\n"
        "- What roof age triggers a referral?\n"
        "- What endorsement fits a property with a basement?\n"
        "- What is the cash surrender value of a whole life policy? *(unanswerable)*"
    )


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title("🏠 Home Insurance Agent Assistant")
st.caption(
    "Ask HO3/HO5 underwriting questions — answers are grounded in the guideline "
    "corpus and cited. Out-of-corpus questions are refused, not hallucinated."
)


# ---------------------------------------------------------------------------
# Chat state + replay
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []


def render_assistant(result: dict) -> None:
    """Render one assistant turn: answer, sources, retrieved chunks, status."""
    if result["fallback"]:
        st.warning(result["answer"])
    else:
        st.markdown(result["answer"])

    if result["citations"]:
        st.markdown("**Sources:** " + ", ".join(f"`{c}`" for c in result["citations"]))

    chunks = result.get("chunks", [])
    if chunks:
        label = f"🔍 Retrieved context ({len(chunks)} chunks)"
        with st.expander(label):
            for i, c in enumerate(chunks, 1):
                score = c.get("rerank_score")
                score_txt = f" · relevance **{score:.1f}**/10" if score is not None else ""
                via = c.get("retrieval", "")
                via_txt = f" · via _{via}_" if via else ""
                st.markdown(f"**[{i}] `{c['source']}`**{score_txt}{via_txt}")
                st.text(c["text"][:600] + ("…" if len(c["text"]) > 600 else ""))
                if i < len(chunks):
                    st.divider()

    top = result.get("top_relevance")
    if top is not None:
        st.caption(f"Top relevance score: {top:.1f}/10  ·  "
                   f"{'refused' if result['fallback'] else 'answered'}")


# Replay history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_assistant(msg["result"])


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask an underwriting question..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Retrieving + generating..."):
            reranker = get_reranker() if use_rerank else None
            retriever = get_retriever(namespace)
            result = answer(prompt, retriever, reranker=reranker)
        render_assistant(result)

    st.session_state.messages.append({"role": "assistant", "result": result})
