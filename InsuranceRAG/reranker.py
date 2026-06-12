"""
reranker.py — LLM cross-encoder-style reranking via Nebius Token Factory.

The hybrid retriever (dense + BM25 + RRF) produces a candidate pool ordered by
fusion score. RRF only knows *rank position* in each list — it never actually
reads the query against the passage. The reranker closes that gap: it scores
how well each candidate answers the specific question (0-10) in a single
batched LLM call, then reorders.

Two things this buys us:
  1. Better top-k ordering (measured as a recall lift in eval.py).
  2. A real "I don't know" signal — if the best candidate scores below
     MIN_RELEVANCE_SCORE, nothing in the corpus actually answers the question,
     so rag.py refuses instead of hallucinating.
"""

import json
import re

from nebius import get_nebius_client, rerank_model

# Below this best-candidate score (0-10), treat the question as unanswerable.
MIN_RELEVANCE_SCORE = 3

_RERANK_SYSTEM = (
    "You are a strict search-relevance judge for an insurance underwriting "
    "assistant. You rate how well each passage answers the user's question."
)

_RERANK_TEMPLATE = """Question: {query}

Passages:
{passages}

Score EVERY passage from 0 to 10 for how well it answers the question:
  10 = directly and fully answers it
  5  = related/topical but only partial
  0  = unrelated

Return ONLY a JSON object of this exact shape, with one entry per passage:
{{"scores": [{{"index": <passage number>, "score": <0-10>}}]}}"""

# Cap passage length in the prompt to keep token usage bounded.
_MAX_PASSAGE_CHARS = 600


class LLMReranker:
    """Reranks retrieval candidates with a single batched Nebius LLM call."""

    def __init__(self, model: str | None = None):
        self.client = get_nebius_client()
        self.model = model or rerank_model()

    def rerank(self, query: str, candidates: list[dict], top_k: int) -> list[dict]:
        """
        Return the top_k candidates reordered by relevance.

        Each returned chunk gains a "rerank_score" key (0-10). On any failure
        (empty input, API error, unparseable response) we fall back to the
        original order so the pipeline degrades gracefully rather than breaking.
        """
        if not candidates:
            return []

        numbered = "\n\n".join(
            f"[{i + 1}] (source: {c['source']})\n{c['text'][:_MAX_PASSAGE_CHARS]}"
            for i, c in enumerate(candidates)
        )
        prompt = _RERANK_TEMPLATE.format(query=query, passages=numbered)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _RERANK_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
            scores = self._parse_scores(response.choices[0].message.content, len(candidates))
        except Exception as exc:  # noqa: BLE001 — graceful degradation is the point
            print(f"  [reranker] falling back to fusion order ({exc})")
            scores = {i: 0.0 for i in range(len(candidates))}

        for i, c in enumerate(candidates):
            c["rerank_score"] = scores.get(i, 0.0)

        ranked = sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _parse_scores(content: str, n: int) -> dict[int, float]:
        """Parse {"scores": [{"index": 1, "score": 8}, ...]} into {0-based idx: score}."""
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("no JSON object in reranker response")
        data = json.loads(match.group(0))

        result: dict[int, float] = {}
        for entry in data.get("scores", []):
            idx = int(entry["index"]) - 1  # passages are 1-indexed in the prompt
            if 0 <= idx < n:
                result[idx] = float(entry["score"])
        if not result:
            raise ValueError("reranker returned no usable scores")
        return result
