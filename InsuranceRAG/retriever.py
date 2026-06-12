"""
retriever.py — Hybrid retrieval (dense + BM25) with Reciprocal Rank Fusion,
plus an optional LLM reranking stage.

Dense:   OpenAI text-embedding-3-small → Pinecone vector search
Sparse:  BM25 over the guideline text, chunked with the SAME strategy as the
         namespace (so the chunking comparison stays apples-to-apples)
Merge:   Reciprocal Rank Fusion (RRF)
Rerank:  optional LLMReranker (Nebius) over the fused candidate pool

Usage (standalone):
    python retriever.py "What roof age triggers a referral?"
    python retriever.py --no-rerank "What roof age triggers a referral?"
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from rank_bm25 import BM25Okapi

from chunking import load_and_chunk

load_dotenv()

GUIDELINES_DIR = Path(__file__).parent / "data" / "guidelines"
EMBEDDING_MODEL = "text-embedding-3-small"
PINECONE_INDEX = os.environ["PINECONE_INDEX_NAME"]
TOP_K = 5
# Size of the fused pool fed into the reranker (must be >= TOP_K to leave the
# reranker room to reorder). Ignored when reranking is off.
CANDIDATE_K = 10
RRF_K = 60  # RRF constant — larger value reduces impact of high ranks


# ---------------------------------------------------------------------------
# BM25 index (built in-memory from raw files each run — corpus is small)
# ---------------------------------------------------------------------------

def build_bm25_corpus(strategy: str) -> tuple[BM25Okapi, list[dict]]:
    """Load all guideline chunks for a strategy and build a BM25 index."""
    docs = load_and_chunk(GUIDELINES_DIR, strategy)
    tokenized = [doc["text"].lower().split() for doc in docs]
    bm25 = BM25Okapi(tokenized)
    return bm25, docs


# ---------------------------------------------------------------------------
# RRF merge
# ---------------------------------------------------------------------------

def reciprocal_rank_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    k: int = RRF_K,
) -> list[dict]:
    """
    Merge two ranked lists using Reciprocal Rank Fusion.
    Each result must have a 'text' key for deduplication.
    Returns list sorted by combined RRF score (descending).
    """
    scores: dict[str, float] = {}
    docs_by_key: dict[str, dict] = {}

    for rank, doc in enumerate(dense_results):
        key = doc["text"][:120]  # use text prefix as dedup key
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        docs_by_key[key] = doc

    for rank, doc in enumerate(sparse_results):
        key = doc["text"][:120]
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        docs_by_key[key] = doc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs_by_key[key] for key, _ in ranked]


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------

class HybridRetriever:
    def __init__(self, namespace: str = "paragraph", reranker=None):
        self.namespace = namespace
        self.reranker = reranker
        self.embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)
        self.vector_store = PineconeVectorStore(
            index_name=PINECONE_INDEX,
            embedding=self.embeddings,
            namespace=namespace,
        )
        # BM25 chunks the SAME way as this namespace so the sparse and dense
        # sides agree on what a "chunk" is for the chosen strategy.
        print(f"  Building BM25 index ({namespace}) from {GUIDELINES_DIR}...")
        self.bm25, self.bm25_corpus = build_bm25_corpus(namespace)
        print(f"  BM25 corpus: {len(self.bm25_corpus)} chunks.")

    def retrieve(self, query: str, top_k: int = TOP_K, reranker=...) -> list[dict]:
        """
        Return top_k chunks using hybrid RRF retrieval, optionally reranked.

        reranker: pass an LLMReranker to rerank, None to skip, or leave as the
        default sentinel to use the reranker configured on the instance.
        """
        reranker = self.reranker if reranker is ... else reranker

        # When reranking we fuse a larger pool and let the reranker pick top_k.
        pool_k = max(CANDIDATE_K, top_k) if reranker is not None else top_k

        # --- Dense retrieval via Pinecone ---
        dense_docs = self.vector_store.similarity_search(query, k=pool_k * 2)
        dense_results = [
            {
                "text": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "retrieval": "dense",
            }
            for doc in dense_docs
        ]

        # --- Sparse retrieval via BM25 ---
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)
        top_indices = sorted(
            range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True
        )[: pool_k * 2]
        sparse_results = [
            {
                "text": self.bm25_corpus[i]["text"],
                "source": self.bm25_corpus[i]["source"],
                "retrieval": "sparse",
            }
            for i in top_indices
        ]

        # --- RRF merge ---
        merged = reciprocal_rank_fusion(dense_results, sparse_results)

        # --- Optional rerank over the fused pool ---
        if reranker is not None:
            return reranker.rerank(query, merged[:pool_k], top_k)
        return merged[:top_k]


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    use_rerank = True
    if "--no-rerank" in args:
        use_rerank = False
        args.remove("--no-rerank")

    query = " ".join(args) if args else "What roof age triggers a referral?"
    print(f"\nQuery: {query}  (rerank={'on' if use_rerank else 'off'})\n")

    reranker = None
    if use_rerank:
        from reranker import LLMReranker
        reranker = LLMReranker()

    retriever = HybridRetriever(reranker=reranker)
    results = retriever.retrieve(query)

    print(f"\nTop {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        score = f" | rerank={r['rerank_score']:.1f}" if "rerank_score" in r else ""
        print(f"[{i}] Source: {r['source']} | via: {r['retrieval']}{score}")
        print(f"    {r['text'][:200]}...")
        print()
