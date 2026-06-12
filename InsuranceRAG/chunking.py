"""
chunking.py — Shared chunking strategies used by both ingest and retrieval.

Two strategies are compared throughout the project:
  - fixed:     RecursiveCharacterTextSplitter at ~512 chars with overlap
  - paragraph: Split on blank lines (section-aware, variable size)

Keeping these here means the dense side (ingest.py) and the sparse BM25 side
(retriever.py) chunk identically for a given strategy, so the chunking
comparison in eval.py is apples-to-apples.
"""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

STRATEGIES = ["fixed", "paragraph"]


def chunk_fixed(text: str, source: str) -> list[dict]:
    """Split into ~512-char chunks with 50-char overlap."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=50,
        separators=["\n## ", "\n### ", "\n\n", "\n", " "],
    )
    chunks = splitter.split_text(text)
    return [
        {"text": c, "source": source, "chunk_strategy": "fixed", "chunk_index": i}
        for i, c in enumerate(chunks)
    ]


def chunk_paragraph(text: str, source: str) -> list[dict]:
    """Split on blank lines — keeps each section/paragraph intact."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    return [
        {"text": p, "source": source, "chunk_strategy": "paragraph", "chunk_index": i}
        for i, p in enumerate(paragraphs)
    ]


def chunk_text(text: str, source: str, strategy: str) -> list[dict]:
    """Dispatch to the requested chunking strategy."""
    if strategy == "fixed":
        return chunk_fixed(text, source)
    if strategy == "paragraph":
        return chunk_paragraph(text, source)
    raise ValueError(f"Unknown chunk strategy: {strategy!r} (expected one of {STRATEGIES})")


def load_and_chunk(guidelines_dir: Path, strategy: str) -> list[dict]:
    """Read every .md file in a directory and chunk it with the given strategy."""
    docs: list[dict] = []
    for path in sorted(guidelines_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        docs.extend(chunk_text(text, path.name, strategy))
    return docs
