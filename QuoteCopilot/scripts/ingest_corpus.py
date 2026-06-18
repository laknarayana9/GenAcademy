"""Build and validate retrieval indexes from the guideline corpus.

The HybridRetriever builds its indexes in memory on first use, so this script's
job is to (a) validate the corpus chunks cleanly, (b) warm the semantic model and
persist embeddings to ChromaDB when available, and (c) print a summary the README
can reference. It is safe to run repeatedly.

Usage:
    python scripts/ingest_corpus.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.tools.rag import load_chunks  # noqa: E402


def main() -> int:
    settings = get_settings()
    settings.ensure_data_dirs()

    corpus_dir = settings.corpus_dir
    if not corpus_dir.exists():
        print(f"ERROR: corpus directory not found: {corpus_dir}")
        return 1

    chunks = load_chunks(corpus_dir)
    if not chunks:
        print(f"ERROR: no chunks produced from {corpus_dir}")
        return 1

    docs = sorted({c.doc_id for c in chunks})
    print("QuoteCopilot corpus ingestion")
    print("-" * 40)
    print(f"corpus dir : {corpus_dir}")
    print(f"documents  : {len(docs)}")
    print(f"chunks     : {len(chunks)}")
    for doc in docs:
        n = sum(1 for c in chunks if c.doc_id == doc)
        print(f"  - {doc}: {n} chunks")

    # Optionally persist embeddings to ChromaDB if the stack is installed.
    try:
        import chromadb  # noqa: WPS433
        from sentence_transformers import SentenceTransformer  # noqa: WPS433

        print("-" * 40)
        print("Building semantic index (ChromaDB)...")
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        collection = client.get_or_create_collection("quotecopilot_guidelines")
        embedder = SentenceTransformer(settings.embedding_model)
        embeddings = embedder.encode(
            [c.text for c in chunks], normalize_embeddings=True
        ).tolist()
        collection.upsert(
            ids=[c.chunk_id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[
                {"doc_id": c.doc_id, "section": c.section, "source": c.source_file}
                for c in chunks
            ],
        )
        print(f"semantic index persisted to {settings.chroma_dir}")
    except Exception as exc:  # noqa: BLE001
        print("-" * 40)
        print(f"Semantic index skipped (optional deps unavailable): {exc}")
        print("Lexical BM25/fallback retrieval will be used at runtime.")

    print("-" * 40)
    print("Ingestion complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
