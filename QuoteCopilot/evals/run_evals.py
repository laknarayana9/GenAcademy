"""Evaluation harness for QuoteCopilot.

Runs each labeled case through the orchestrator (no checkpointer needed — the
graph is deterministic, so resume is modeled by re-invoking with answers merged
into a fresh state) and scores decision accuracy, reason-code match, missing-info
detection, citation faithfulness, and review-required match.

Usage:
    python evals/run_evals.py            # run and print summary
    python evals/run_evals.py --report   # same, plus write results JSON
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402
from app.graph.orchestrator import build_orchestrator  # noqa: E402
from app.graph.state import new_run_state  # noqa: E402
from app.tools.rag import load_chunks  # noqa: E402

DATASET = Path(__file__).resolve().parent / "dataset.json"


def _valid_chunk_ids() -> set[str]:
    settings = get_settings()
    return {c.chunk_id for c in load_chunks(settings.corpus_dir)}


def _run_case(graph, case: dict) -> dict:
    """Run a single case end to end, resuming if answers are provided."""
    state = new_run_state(case["case_id"], case["input"].get("quote_id", "q"),
                          case["input"])
    first = graph.invoke(state)
    detected_missing = list(first.get("missing_info", []))

    final = first
    if first.get("status") == "waiting_for_info" and "answers" in case:
        resume_state = new_run_state(
            case["case_id"], case["input"].get("quote_id", "q"), case["input"]
        )
        resume_state["additional_answers"] = case["answers"]
        final = graph.invoke(resume_state)
        # A second pause (e.g. wildfire) would require another answer set.
        if final.get("status") == "waiting_for_info":
            detected_missing += list(final.get("missing_info", []))

    return {"first": first, "final": final, "detected_missing": detected_missing}


def _score_case(case: dict, result: dict, valid_ids: set[str]) -> dict:
    expected = case["expected"]
    final = result["final"]
    packet = final.get("decision_packet", {}) or {}

    got_rec = packet.get("recommendation")
    decision_ok = got_rec == expected["recommendation"]

    got_codes = {rc.get("code") for rc in packet.get("reason_codes", [])}
    expected_codes = set(expected.get("reason_codes", []))
    reason_ok = expected_codes.issubset(got_codes)

    missing_ok = set(result["detected_missing"]) == set(
        expected.get("missing_info_fields", [])
    ) or (not expected.get("missing_info_fields") and not result["detected_missing"])

    review_required = final.get("status") == "pending_review"
    review_ok = review_required == expected.get("review_required", False)

    citations = packet.get("citations", [])
    faithful = all(c.get("chunk_id") in valid_ids for c in citations)

    return {
        "case_id": case["case_id"],
        "decision_ok": decision_ok,
        "reason_ok": reason_ok,
        "missing_ok": missing_ok,
        "review_ok": review_ok,
        "faithful": faithful,
        "got": {
            "recommendation": got_rec,
            "reason_codes": sorted(got_codes),
            "missing": sorted(set(result["detected_missing"])),
            "review_required": review_required,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", action="store_true", help="write results JSON")
    args = parser.parse_args()

    data = json.loads(DATASET.read_text(encoding="utf-8"))
    cases = data["cases"]
    valid_ids = _valid_chunk_ids()
    graph = build_orchestrator(checkpointer=None)

    scores = []
    for case in cases:
        result = _run_case(graph, case)
        scores.append(_score_case(case, result, valid_ids))

    n = len(scores)
    metrics = {
        "decision_accuracy": sum(s["decision_ok"] for s in scores) / n,
        "reason_code_match": sum(s["reason_ok"] for s in scores) / n,
        "missing_info_detection": sum(s["missing_ok"] for s in scores) / n,
        "review_required_match": sum(s["review_ok"] for s in scores) / n,
        "citation_faithfulness": sum(s["faithful"] for s in scores) / n,
    }

    print("\nQuoteCopilot evaluation")
    print("=" * 60)
    header = f"{'case':22} {'dec':4} {'rsn':4} {'mis':4} {'rev':4} {'cite':4}"
    print(header)
    print("-" * 60)
    for s in scores:
        print(
            f"{s['case_id']:22} "
            f"{'Y' if s['decision_ok'] else 'N':4} "
            f"{'Y' if s['reason_ok'] else 'N':4} "
            f"{'Y' if s['missing_ok'] else 'N':4} "
            f"{'Y' if s['review_ok'] else 'N':4} "
            f"{'Y' if s['faithful'] else 'N':4}"
        )
    print("-" * 60)
    for name, value in metrics.items():
        print(f"{name:28}: {value:6.1%}")
    print("=" * 60)

    if args.report:
        out_dir = Path(__file__).resolve().parent / "results"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{date.today().isoformat()}.json"
        out_path.write_text(
            json.dumps({"metrics": metrics, "cases": scores}, indent=2),
            encoding="utf-8",
        )
        print(f"results written to {out_path}")

    # Non-zero exit if any core metric below target, useful for CI.
    ok = metrics["decision_accuracy"] >= 0.95 and metrics["citation_faithfulness"] >= 1.0
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
