"""SQLite connection and data-access helpers for the business database.

This module owns `quotecopilot.db`. All business reads/writes go through the
`Database` class. LangGraph's checkpoint DB is intentionally separate and never
touched here. JSON-typed columns are (de)serialized at this boundary so callers
work with native Python structures.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def _utc_now() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Thin data-access layer over the QuoteCopilot business SQLite store."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    # --- lifecycle -----------------------------------------------------
    def migrate(self) -> None:
        """Apply the schema. Safe to call repeatedly (IF NOT EXISTS)."""
        self._conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    # --- runs ----------------------------------------------------------
    def create_run(self, run_id: str, quote_id: str, status: str) -> None:
        now = _utc_now()
        self._conn.execute(
            "INSERT OR IGNORE INTO runs (run_id, quote_id, status, current_node, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (run_id, quote_id, status, None, now, now),
        )
        self._conn.commit()

    def update_run_status(
        self, run_id: str, status: str, current_node: str | None = None
    ) -> None:
        self._conn.execute(
            "UPDATE runs SET status = ?, current_node = COALESCE(?, current_node), "
            "updated_at = ? WHERE run_id = ?",
            (status, current_node, _utc_now(), run_id),
        )
        self._conn.commit()

    def get_run(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_runs(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- decision packets ---------------------------------------------
    def upsert_decision_packet(self, run_id: str, packet: dict) -> None:
        self._conn.execute(
            "INSERT INTO decision_packets (run_id, recommendation, confidence, "
            "reason_codes, citations, facts_used, premium_indication, next_steps, "
            "review_status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET "
            "recommendation=excluded.recommendation, confidence=excluded.confidence, "
            "reason_codes=excluded.reason_codes, citations=excluded.citations, "
            "facts_used=excluded.facts_used, premium_indication=excluded.premium_indication, "
            "next_steps=excluded.next_steps, review_status=excluded.review_status",
            (
                run_id,
                packet.get("recommendation"),
                packet.get("confidence"),
                json.dumps(packet.get("reason_codes", [])),
                json.dumps(packet.get("citations", [])),
                json.dumps(packet.get("facts_used", {})),
                packet.get("premium_indication"),
                json.dumps(packet.get("next_steps", [])),
                packet.get("review_status"),
                _utc_now(),
            ),
        )
        self._conn.commit()

    def get_decision_packet(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM decision_packets WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        packet = dict(row)
        for field in ("reason_codes", "citations", "facts_used", "next_steps"):
            if packet.get(field) is not None:
                packet[field] = json.loads(packet[field])
        return packet

    # --- audit events --------------------------------------------------
    def add_audit_event(
        self, run_id: str, node: str, event_type: str, payload: dict | None = None
    ) -> None:
        self._conn.execute(
            "INSERT INTO audit_events (run_id, node, event_type, payload, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (run_id, node, event_type, json.dumps(payload or {}), _utc_now()),
        )
        self._conn.commit()

    def get_audit_events(self, run_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM audit_events WHERE run_id = ? ORDER BY id ASC", (run_id,)
        ).fetchall()
        events = []
        for r in rows:
            event = dict(r)
            if event.get("payload") is not None:
                event["payload"] = json.loads(event["payload"])
            events.append(event)
        return events

    # --- pending questions (paused runs) ------------------------------
    def set_pending_questions(self, run_id: str, questions: list[dict]) -> None:
        self._conn.execute(
            "INSERT INTO pending_questions (run_id, questions, created_at) "
            "VALUES (?, ?, ?) ON CONFLICT(run_id) DO UPDATE SET "
            "questions=excluded.questions, created_at=excluded.created_at",
            (run_id, json.dumps(questions), _utc_now()),
        )
        self._conn.commit()

    def get_pending_questions(self, run_id: str) -> list[dict]:
        row = self._conn.execute(
            "SELECT questions FROM pending_questions WHERE run_id = ?", (run_id,)
        ).fetchone()
        return json.loads(row["questions"]) if row else []

    def clear_pending_questions(self, run_id: str) -> None:
        self._conn.execute(
            "DELETE FROM pending_questions WHERE run_id = ?", (run_id,)
        )
        self._conn.commit()

    # --- review tasks --------------------------------------------------
    def upsert_review_task(self, task: dict) -> None:
        now = _utc_now()
        self._conn.execute(
            "INSERT INTO review_tasks (run_id, status, priority, trigger, "
            "review_packet, reviewer_note, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, "
            "priority=excluded.priority, trigger=excluded.trigger, "
            "review_packet=excluded.review_packet, reviewer_note=excluded.reviewer_note, "
            "updated_at=excluded.updated_at",
            (
                task["run_id"],
                task.get("status", "pending"),
                task.get("priority", "medium"),
                task["trigger"],
                json.dumps(task.get("review_packet", {})),
                task.get("reviewer_note"),
                now,
                now,
            ),
        )
        self._conn.commit()

    def update_review_task(
        self, run_id: str, status: str, reviewer_note: str | None = None
    ) -> None:
        self._conn.execute(
            "UPDATE review_tasks SET status = ?, "
            "reviewer_note = COALESCE(?, reviewer_note), updated_at = ? "
            "WHERE run_id = ?",
            (status, reviewer_note, _utc_now(), run_id),
        )
        self._conn.commit()

    def get_review_task(self, run_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM review_tasks WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        task = dict(row)
        if task.get("review_packet") is not None:
            task["review_packet"] = json.loads(task["review_packet"])
        return task

    def list_pending_reviews(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM review_tasks WHERE status = 'pending' "
            "ORDER BY CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 "
            "ELSE 2 END, created_at ASC"
        ).fetchall()
        tasks = []
        for r in rows:
            task = dict(r)
            if task.get("review_packet") is not None:
                task["review_packet"] = json.loads(task["review_packet"])
            tasks.append(task)
        return tasks
