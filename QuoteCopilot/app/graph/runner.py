"""Graph invocation, resume, and persistence wiring.

The runner is the only place that combines the LangGraph orchestrator with the
business database. Agents stay pure; the runner persists audit events, run
status, decision packets, and review tasks as a post-invocation step.

Resume semantics: a paused run is re-invoked on the same ``thread_id`` with the
supplied answers merged into state. Because the SqliteSaver checkpoint preserves
accumulated state and the agents are deterministic, replay completes the run with
the previously missing facts resolved.
"""

from __future__ import annotations

import contextlib
from typing import Any

from app.config import get_settings
from app.db.connection import Database
from app.graph.orchestrator import build_orchestrator
from app.graph.state import new_run_state


class GraphRunner:
    """Owns the compiled graph + checkpointer and persists run outcomes."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self.settings = get_settings()
        self.settings.ensure_data_dirs()
        self._cm = None
        self._checkpointer = self._make_checkpointer()
        self.graph = build_orchestrator(checkpointer=self._checkpointer)

    def _make_checkpointer(self):
        """Create a SqliteSaver, falling back to in-memory if unavailable."""
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver

            self._cm = SqliteSaver.from_conn_string(
                str(self.settings.checkpoint_db_path)
            )
            return self._cm.__enter__()
        except Exception:  # noqa: BLE001
            with contextlib.suppress(Exception):
                from langgraph.checkpoint.memory import MemorySaver

                return MemorySaver()
            return None

    # --- public API ----------------------------------------------------
    def start(self, run_id: str, quote_id: str, submission_raw: dict) -> dict:
        """Begin a new run and persist its outcome."""
        self.db.create_run(run_id, quote_id, "processing")
        state = new_run_state(run_id, quote_id, submission_raw)
        return self._invoke(run_id, state)

    def resume(self, run_id: str, answers: dict) -> dict:
        """Resume a paused run with supplied answers on the same thread_id."""
        self.db.update_run_status(run_id, "processing")
        self.db.clear_pending_questions(run_id)
        # Re-seed raw submission so re-normalization sees prior + new facts.
        run = self.db.get_run(run_id)
        quote_id = run["quote_id"] if run else run_id
        prior = self._current_state(run_id)
        submission_raw = dict(prior.get("submission_raw", {}))
        merged_answers = dict(prior.get("additional_answers", {}))
        merged_answers.update(answers)
        state = new_run_state(run_id, quote_id, submission_raw)
        state["additional_answers"] = merged_answers
        return self._invoke(run_id, state)

    # --- internals -----------------------------------------------------
    def _config(self, run_id: str) -> dict:
        return {"configurable": {"thread_id": run_id}}

    def _current_state(self, run_id: str) -> dict:
        with contextlib.suppress(Exception):
            snapshot = self.graph.get_state(self._config(run_id))
            if snapshot and snapshot.values:
                return snapshot.values
        return {}

    def _invoke(self, run_id: str, state: dict) -> dict:
        try:
            final = self.graph.invoke(state, config=self._config(run_id))
        except Exception as exc:  # noqa: BLE001
            self.db.update_run_status(run_id, "failed")
            self.db.add_audit_event(run_id, "runner", "failed", {"error": str(exc)})
            return {"run_id": run_id, "status": "failed", "error": str(exc)}
        return self._persist(run_id, final)

    def _persist(self, run_id: str, state: dict) -> dict:
        status = state.get("status", "processing")
        current_node = state.get("current_node")

        # Audit events accumulated on the state channel.
        for event in state.get("events", []):
            self.db.add_audit_event(
                run_id,
                event.get("node", "?"),
                event.get("event_type", "?"),
                event.get("payload", {}),
            )

        if status == "waiting_for_info":
            self.db.set_pending_questions(run_id, state.get("required_questions", []))

        packet = state.get("decision_packet") or {}
        if packet:
            self.db.upsert_decision_packet(run_id, packet)

        if status == "pending_review":
            self._persist_review_task(run_id, state)

        self.db.update_run_status(run_id, status, current_node)

        return {
            "run_id": run_id,
            "status": status,
            "required_questions": state.get("required_questions", []),
        }

    def _persist_review_task(self, run_id: str, state: dict) -> None:
        verification = state.get("verification", {}) or {}
        task_meta = verification.get("review_task", {})
        self.db.upsert_review_task(
            {
                "run_id": run_id,
                "status": "pending",
                "priority": task_meta.get("priority", "medium"),
                "trigger": task_meta.get("trigger", "refer"),
                "review_packet": task_meta.get("review_packet", {}),
            }
        )

    def close(self) -> None:
        if self._cm is not None:
            with contextlib.suppress(Exception):
                self._cm.__exit__(None, None, None)


def run_once(submission_raw: dict, db: Database, run_id: str, quote_id: str) -> dict:
    """Convenience one-shot helper used by evals/tests."""
    runner = GraphRunner(db)
    try:
        return runner.start(run_id, quote_id, submission_raw)
    finally:
        runner.close()
