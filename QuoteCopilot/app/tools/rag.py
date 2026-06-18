"""Hybrid retrieval over the synthetic guideline corpus.

Pipeline per query intent:
1. BM25 lexical retrieval (exact rule-term matching).
2. Semantic retrieval via sentence-transformers embeddings (paraphrase coverage).
3. Reciprocal Rank Fusion (RRF) to merge the two ranked lists.
4. Cross-encoder re-ranking to return the top-k.

Heavy dependencies (rank_bm25, sentence-transformers, chromadb) are optional at
runtime: the retriever degrades gracefully to a lightweight lexical scorer when
they are unavailable, so the system remains runnable and testable without a full
ML stack or prebuilt indexes. The corpus is chunked in memory on first use.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.config import get_settings

# --- Optional heavy dependencies (imported defensively) --------------------
try:  # pragma: no cover - availability depends on environment
    from rank_bm25 import BM25Okapi

    _HAS_BM25 = True
except Exception:  # noqa: BLE001
    _HAS_BM25 = False

try:  # pragma: no cover
    from sentence_transformers import CrossEncoder, SentenceTransformer

    _HAS_ST = True
except Exception:  # noqa: BLE001
    _HAS_ST = False


CHUNK_TARGET_WORDS = 120
CHUNK_OVERLAP_WORDS = 20


@dataclass
class Chunk:
    """A retrievable guideline passage."""

    chunk_id: str
    doc_id: str
    section: str
    text: str
    source_file: str

    def as_citation(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "source": self.source_file,
            "section": self.section,
            "text": self.text,
        }


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    """Split a markdown doc into (section_heading, body) pairs."""
    sections: list[tuple[str, str]] = []
    current_heading = "Preamble"
    buffer: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("##"):
            if buffer:
                sections.append((current_heading, "\n".join(buffer).strip()))
                buffer = []
            current_heading = line.lstrip("#").strip()
        else:
            buffer.append(line)
    if buffer:
        sections.append((current_heading, "\n".join(buffer).strip()))
    return [(h, b) for h, b in sections if b]


def _chunk_body(body: str) -> list[str]:
    """Word-window chunking with overlap."""
    words = body.split()
    if len(words) <= CHUNK_TARGET_WORDS:
        return [body] if body.strip() else []
    chunks = []
    step = CHUNK_TARGET_WORDS - CHUNK_OVERLAP_WORDS
    for start in range(0, len(words), step):
        window = words[start : start + CHUNK_TARGET_WORDS]
        if window:
            chunks.append(" ".join(window))
        if start + CHUNK_TARGET_WORDS >= len(words):
            break
    return chunks


def load_chunks(corpus_dir: Path) -> list[Chunk]:
    """Load and chunk every markdown file in the corpus directory."""
    chunks: list[Chunk] = []
    for path in sorted(corpus_dir.glob("*.md")):
        doc_id = path.stem
        markdown = path.read_text(encoding="utf-8")
        for section, body in _split_sections(markdown):
            for i, piece in enumerate(_chunk_body(body)):
                chunk_id = f"{doc_id}::{_slug(section)}::{i}"
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=doc_id,
                        section=section,
                        text=piece,
                        source_file=path.name,
                    )
                )
    return chunks


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def _rrf(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Reciprocal Rank Fusion over multiple ranked id lists."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)
    return scores


class HybridRetriever:
    """Lazy hybrid retriever with graceful degradation."""

    def __init__(self, corpus_dir: Path, top_k: int = 5) -> None:
        self.corpus_dir = corpus_dir
        self.top_k = top_k
        self.chunks: list[Chunk] = load_chunks(corpus_dir)
        self._by_id = {c.chunk_id: c for c in self.chunks}
        self._tokenized = [_tokenize(c.text) for c in self.chunks]

        self._bm25 = BM25Okapi(self._tokenized) if _HAS_BM25 else None
        self._embedder = None
        self._embeddings = None
        self._cross_encoder = None
        if _HAS_ST:
            self._init_semantic()

    def _init_semantic(self) -> None:  # pragma: no cover - heavy
        settings = get_settings()
        try:
            self._embedder = SentenceTransformer(settings.embedding_model)
            self._embeddings = self._embedder.encode(
                [c.text for c in self.chunks], normalize_embeddings=True
            )
            self._cross_encoder = CrossEncoder(settings.cross_encoder_model)
        except Exception:  # noqa: BLE001
            self._embedder = None
            self._embeddings = None
            self._cross_encoder = None

    # --- per-modality ranking -----------------------------------------
    def _bm25_rank(self, query: str, n: int = 10) -> list[str]:
        if self._bm25 is not None:
            scores = self._bm25.get_scores(_tokenize(query))
            order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            return [self.chunks[i].chunk_id for i in order[:n] if scores[order[0]] > 0]
        # Fallback: token-overlap scoring.
        q = set(_tokenize(query))
        scored = [
            (len(q & set(toks)), self.chunks[i].chunk_id)
            for i, toks in enumerate(self._tokenized)
        ]
        scored.sort(reverse=True)
        return [cid for s, cid in scored[:n] if s > 0]

    def _semantic_rank(self, query: str, n: int = 10) -> list[str]:  # pragma: no cover
        if self._embedder is None or self._embeddings is None:
            return []
        q_emb = self._embedder.encode([query], normalize_embeddings=True)[0]
        sims = self._embeddings @ q_emb
        order = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)
        return [self.chunks[i].chunk_id for i in order[:n]]

    def _rerank(self, query: str, ids: list[str]) -> list[str]:  # pragma: no cover
        if self._cross_encoder is None or not ids:
            return ids
        pairs = [(query, self._by_id[cid].text) for cid in ids]
        scores = self._cross_encoder.predict(pairs)
        ranked = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in ranked]

    # --- public API ----------------------------------------------------
    def retrieve(self, query: str) -> list[Chunk]:
        """Retrieve top-k chunks for a single query string."""
        bm25_ids = self._bm25_rank(query)
        semantic_ids = self._semantic_rank(query)
        rankings = [r for r in (bm25_ids, semantic_ids) if r]
        if not rankings:
            return []
        fused = _rrf(rankings)
        candidate_ids = sorted(fused, key=lambda c: fused[c], reverse=True)[:10]
        reranked = self._rerank(query, candidate_ids)
        return [self._by_id[cid] for cid in reranked[: self.top_k]]

    def retrieve_plan(self, plan: dict) -> dict:
        """Run a retrieval plan (list of query intents) and dedupe results.

        Returns a dict with ``chunks`` (citation dicts), ``source_metadata``,
        and ``retrieval_metrics`` suitable for writing into RunState.retrieval.
        """
        seen: dict[str, Chunk] = {}
        per_intent: list[dict] = []
        for query in _plan_queries(plan):
            hits = self.retrieve(query)
            per_intent.append({"query": query, "hit_ids": [h.chunk_id for h in hits]})
            for h in hits:
                seen.setdefault(h.chunk_id, h)
        chunks = [c.as_citation() for c in seen.values()]
        return {
            "chunks": chunks,
            "source_metadata": sorted({c["source"] for c in chunks}),
            "retrieval_metrics": {
                "intents": len(per_intent),
                "unique_chunks": len(chunks),
                "bm25": _HAS_BM25 or "fallback",
                "semantic": self._embedder is not None,
                "per_intent": per_intent,
            },
        }


def _plan_queries(plan: dict) -> list[str]:
    """Flatten a retrieval plan into query strings."""
    queries: list[str] = []
    for q in (plan or {}).get("queries", []):
        if isinstance(q, str):
            queries.append(q)
        elif isinstance(q, dict):
            intent = q.get("intent", "")
            keywords = " ".join(q.get("keywords", []))
            queries.append(f"{intent} {keywords}".strip())
    return queries or ["HO3 eligibility referral guidelines"]


@dataclass
class _RetrieverCache:
    retriever: HybridRetriever | None = None
    signature: tuple = field(default_factory=tuple)


@lru_cache(maxsize=1)
def get_retriever() -> HybridRetriever:
    """Return a process-wide retriever built from the configured corpus."""
    settings = get_settings()
    return HybridRetriever(settings.corpus_dir, top_k=settings.retrieval_top_k)
