"""
eval.py — Chunking comparison + reranking impact + end-to-end answer quality.

Produces `comparison_report.md` with three parts:

  1. Retrieval quality matrix — recall@5 for each
     {chunking strategy} x {rerank on/off}. This is both the chunking-strategy
     comparison AND the reranking-impact analysis the project asks for.
     (Retrieval-only, no generation — fast and cheap.)

  2. End-to-end answers — runs the full pipeline (Nebius generation) on the
     best config, scoring answer relevance on answerable questions and refusal
     correctness on the unanswerable ("I don't know" path) questions.

Usage:
    python eval.py
    python eval.py --output comparison_report.md
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from retriever import HybridRetriever, TOP_K
from reranker import LLMReranker
from rag import answer

load_dotenv()

EVAL_QUESTIONS_PATH = Path(__file__).parent / "data" / "eval_questions.json"
NAMESPACES = ["paragraph", "fixed"]
BEST_NAMESPACE = "paragraph"  # config used for the end-to-end answer run


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def score_retrieval(citations: list[str], expected_sources: list[str]) -> bool:
    """True if at least one expected source appears in the retrieved citations."""
    cited = set(citations)
    return any(src in cited for src in expected_sources)


def score_answer(answer_text: str, expected_keywords: list[str]) -> bool:
    """True if at least one expected keyword appears in the answer (case-insensitive)."""
    lower = answer_text.lower()
    return any(kw.lower() in lower for kw in expected_keywords)


def is_answerable(q: dict) -> bool:
    return q.get("answerable", True)


# ---------------------------------------------------------------------------
# Part 1 — retrieval quality matrix (chunking + reranking comparison)
# ---------------------------------------------------------------------------

def retrieval_recall(retriever: HybridRetriever, reranker, questions: list[dict]) -> float:
    """Fraction of answerable questions whose expected source is retrieved."""
    hits = 0
    for q in questions:
        chunks = retriever.retrieve(q["question"], top_k=TOP_K, reranker=reranker)
        sources = [c["source"] for c in chunks]
        if score_retrieval(sources, q["expected_sources"]):
            hits += 1
    return hits / len(questions)


def run_comparison_matrix(questions: list[dict], reranker: LLMReranker) -> dict:
    """Compute recall@k for every (namespace, rerank on/off) combination."""
    answerable = [q for q in questions if is_answerable(q)]
    matrix: dict[tuple[str, bool], float] = {}

    for ns in NAMESPACES:
        retriever = HybridRetriever(namespace=ns)
        for use_rerank in (False, True):
            label = f"{ns} / rerank={'on' if use_rerank else 'off'}"
            print(f"  Scoring retrieval: {label} ...")
            recall = retrieval_recall(
                retriever, reranker if use_rerank else None, answerable
            )
            matrix[(ns, use_rerank)] = recall
            print(f"    recall@{TOP_K} = {recall:.0%}")

    return matrix


# ---------------------------------------------------------------------------
# Part 2 — end-to-end answers on the best config
# ---------------------------------------------------------------------------

def run_end_to_end(questions: list[dict], reranker: LLMReranker) -> list[dict]:
    retriever = HybridRetriever(namespace=BEST_NAMESPACE, reranker=reranker)
    results = []
    for q in questions:
        answerable = is_answerable(q)
        print(f"  Q{q['id']} ({'answerable' if answerable else 'UNANSWERABLE'}): "
              f"{q['question'][:55]}...")
        result = answer(q["question"], retriever)

        if answerable:
            retrieval_pass = score_retrieval(result["citations"], q["expected_sources"])
            answer_pass = score_answer(result["answer"], q["expected_answer_contains"])
            refusal_pass = None
        else:
            # Correct behavior on an unanswerable question is to refuse.
            retrieval_pass = None
            answer_pass = None
            refusal_pass = result["fallback"]

        results.append({
            "id": q["id"],
            "question": q["question"],
            "answerable": answerable,
            "answer": result["answer"],
            "citations": result["citations"],
            "expected_sources": q["expected_sources"],
            "top_relevance": result.get("top_relevance"),
            "fallback": result["fallback"],
            "retrieval_pass": retrieval_pass,
            "answer_pass": answer_pass,
            "refusal_pass": refusal_pass,
        })
        marks = []
        if retrieval_pass is not None:
            marks.append(f"retrieval={'✅' if retrieval_pass else '❌'}")
        if answer_pass is not None:
            marks.append(f"answer={'✅' if answer_pass else '❌'}")
        if refusal_pass is not None:
            marks.append(f"refused={'✅' if refusal_pass else '❌'}")
        print(f"         {'  '.join(marks)}")
    return results


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def _mark(value) -> str:
    if value is None:
        return "—"
    return "✅" if value else "❌"


def build_report(matrix: dict, e2e: list[dict]) -> str:
    answerable = [r for r in e2e if r["answerable"]]
    unanswerable = [r for r in e2e if not r["answerable"]]

    n_ans = len(answerable)
    answer_hits = sum(bool(r["answer_pass"]) for r in answerable)
    retr_hits = sum(bool(r["retrieval_pass"]) for r in answerable)
    refusal_hits = sum(bool(r["refusal_pass"]) for r in unanswerable)

    lines = [
        "# Insurance RAG — Comparison Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "Project 2 — Financial Document Intelligence. Compares two chunking "
        "strategies and measures the impact of an LLM reranking step, then runs "
        "the full pipeline end-to-end (generation via Nebius Token Factory).",
        "",
        "---",
        "",
        "## 1. Retrieval Quality — Chunking × Reranking",
        "",
        f"Metric: **recall@{TOP_K}** — fraction of answerable questions whose "
        "expected source document appears in the retrieved chunks. "
        f"Strategies compared: {', '.join(NAMESPACES)}.",
        "",
        "| Chunking strategy | Rerank off | Rerank on | Δ (rerank impact) |",
        "|---|---|---|---|",
    ]
    for ns in NAMESPACES:
        off = matrix[(ns, False)]
        on = matrix[(ns, True)]
        delta = on - off
        sign = "+" if delta >= 0 else ""
        lines.append(f"| {ns} | {off:.0%} | {on:.0%} | {sign}{delta:.0%} |")

    # Pick winners for the narrative.
    best_off = max(NAMESPACES, key=lambda ns: matrix[(ns, False)])
    best_overall_key = max(matrix, key=lambda k: matrix[k])
    lines += [
        "",
        "**Chunking comparison:** without reranking, "
        f"`{best_off}` chunking gives the best recall "
        f"({matrix[(best_off, False)]:.0%}).",
        "",
        "**Reranking impact:** the LLM reranker (Nebius) reorders a "
        "fused candidate pool of "
        f"{TOP_K * 2}+ chunks down to the top {TOP_K}. Best overall config is "
        f"`{best_overall_key[0]}` with rerank "
        f"{'on' if best_overall_key[1] else 'off'} "
        f"({matrix[best_overall_key]:.0%}).",
        "",
        "---",
        "",
        f"## 2. End-to-End Answers (config: {BEST_NAMESPACE} + rerank)",
        "",
        f"- **Answer relevance (keyword match):** {answer_hits}/{n_ans} "
        f"({answer_hits / n_ans:.0%})",
        f"- **Retrieval recall (source match):** {retr_hits}/{n_ans} "
        f"({retr_hits / n_ans:.0%})",
        (
            "- **Refusal correctness (unanswerable → \"I don't know\"):** "
            f"{refusal_hits}/{len(unanswerable)} "
            f"({refusal_hits / len(unanswerable):.0%})"
            if unanswerable
            else "- **Refusal correctness:** no unanswerable questions in set"
        ),
        "",
        "| # | Type | Question | Retrieval | Answer | Refused | Top score |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in e2e:
        q_short = r["question"][:55] + ("..." if len(r["question"]) > 55 else "")
        typ = "ans" if r["answerable"] else "unans"
        score = f"{r['top_relevance']:.1f}" if r["top_relevance"] is not None else "—"
        lines.append(
            f"| {r['id']} | {typ} | {q_short} | {_mark(r['retrieval_pass'])} | "
            f"{_mark(r['answer_pass'])} | {_mark(r['refusal_pass'])} | {score} |"
        )

    lines += ["", "---", "", "## 3. Detailed Answers", ""]
    for r in e2e:
        typ = "answerable" if r["answerable"] else "unanswerable"
        score = f"{r['top_relevance']:.1f}" if r["top_relevance"] is not None else "—"
        lines += [
            f"### Q{r['id']}: {r['question']}",
            "",
            f"**Type:** {typ}  |  **Top relevance:** {score}",
            "",
            f"**Expected sources:** {', '.join(r['expected_sources']) or 'none (unanswerable)'}",
            f"**Retrieved sources:** {', '.join(r['citations']) if r['citations'] else 'none'}",
            "",
            "**Answer:**",
            "",
            r["answer"],
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Evaluate the Insurance RAG pipeline.")
    parser.add_argument("--output", default="comparison_report.md", help="Output markdown file.")
    args = parser.parse_args()

    print("\n=== Insurance RAG Evaluator ===\n")

    with open(EVAL_QUESTIONS_PATH) as f:
        questions = json.load(f)

    reranker = LLMReranker()

    print("Part 1 — retrieval quality matrix (chunking × reranking):\n")
    matrix = run_comparison_matrix(questions, reranker)

    print("\nPart 2 — end-to-end answers (Nebius generation):\n")
    e2e = run_end_to_end(questions, reranker)

    report = build_report(matrix, e2e)
    Path(args.output).write_text(report, encoding="utf-8")

    print(f"\n{'=' * 50}")
    print("Retrieval recall by config (recall@%d):" % TOP_K)
    for ns in NAMESPACES:
        print(f"  {ns:>10} | off {matrix[(ns, False)]:.0%}  ->  on {matrix[(ns, True)]:.0%}")
    print(f"{'=' * 50}")
    print(f"\nReport saved to: {args.output}")


if __name__ == "__main__":
    main()
