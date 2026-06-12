"""
rag.py — Full RAG pipeline: retrieve → generate → cite.

Usage:
    python rag.py "Is a property with knob-and-tube wiring eligible?"
    python rag.py "What wildfire score triggers a decline?"
"""

import sys
from dotenv import load_dotenv

from retriever import HybridRetriever
from reranker import LLMReranker, MIN_RELEVANCE_SCORE
from nebius import get_nebius_client, generation_model

load_dotenv()

TOP_K = 5
# Minimum number of retrieved chunks required to attempt an answer.
MIN_CHUNKS_THRESHOLD = 1
REFUSAL_TEXT = "I don't have enough information in the guidelines to answer this question."

SYSTEM_PROMPT = """You are an insurance underwriting assistant. Your job is to answer
questions about HO3/HO5 homeowners insurance guidelines based only on the provided
context excerpts.

Rules:
- Answer only from the provided context. Do not use outside knowledge.
- Always cite the source document (filename) for every claim you make.
- If the context does not contain enough information to answer, say exactly:
  "I don't have enough information in the guidelines to answer this question."
- Keep answers concise and factual. Use bullet points for lists of conditions.
- When quoting a rule, include the section reference if visible in the context.
"""


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context block for the prompt."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] Source: {chunk['source']}\n{chunk['text']}")
    return "\n\n---\n\n".join(parts)


def format_citations(chunks: list[dict]) -> str:
    """Build a deduplicated citation list from retrieved chunks."""
    seen = set()
    citations = []
    for i, chunk in enumerate(chunks, 1):
        src = chunk["source"]
        if src not in seen:
            seen.add(src)
            citations.append(f"  [{i}] {src}")
    return "\n".join(citations)


def _best_relevance(chunks: list[dict]) -> float | None:
    """Return the top reranker relevance score, or None if not reranked."""
    scores = [c["rerank_score"] for c in chunks if "rerank_score" in c]
    return max(scores) if scores else None


def answer(query: str, retriever: HybridRetriever, reranker=...) -> dict:
    """
    Run the full RAG pipeline for a single question.

    The "I don't know" path fires when either:
      - too few chunks come back, or
      - the reranker's best candidate scores below MIN_RELEVANCE_SCORE
        (i.e. nothing in the corpus is actually relevant).

    Returns:
        {
            "question": str,
            "answer": str,
            "citations": list[str],
            "chunks_used": int,
            "fallback": bool,
            "top_relevance": float | None,
        }
    """
    chunks = retriever.retrieve(query, top_k=TOP_K, reranker=reranker)
    top_relevance = _best_relevance(chunks)

    insufficient = len(chunks) < MIN_CHUNKS_THRESHOLD
    if top_relevance is not None and top_relevance < MIN_RELEVANCE_SCORE:
        insufficient = True

    if insufficient:
        return {
            "question": query,
            "answer": REFUSAL_TEXT,
            "citations": [],
            "chunks": chunks,
            "chunks_used": len(chunks),
            "fallback": True,
            "top_relevance": top_relevance,
        }

    context = build_context(chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    client = get_nebius_client()
    response = client.chat.completions.create(
        model=generation_model(),
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )

    answer_text = response.choices[0].message.content.strip()
    citations = [chunk["source"] for chunk in chunks]
    unique_citations = list(dict.fromkeys(citations))  # deduplicated, order preserved

    return {
        "question": query,
        "answer": answer_text,
        "citations": unique_citations,
        "chunks": chunks,
        "chunks_used": len(chunks),
        "fallback": False,
        "top_relevance": top_relevance,
    }


def print_result(result: dict) -> None:
    print(f"\nQuestion: {result['question']}")
    print(f"\nAnswer:\n{result['answer']}")
    if result["citations"]:
        print(f"\nSources:")
        for src in result["citations"]:
            print(f"  - {src}")
    if result["fallback"]:
        print("\n[Fallback: insufficient context retrieved]")
    print()


# ---------------------------------------------------------------------------
# Standalone usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "Is a property with knob-and-tube wiring eligible for HO3 coverage?"

    print("Initializing retriever + reranker...")
    reranker = LLMReranker()
    retriever = HybridRetriever(reranker=reranker)

    result = answer(query, retriever)
    print_result(result)
