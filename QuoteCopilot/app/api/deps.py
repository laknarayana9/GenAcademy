"""Shared FastAPI dependencies.

Wires the two process-wide singletons used across routers: the business
``Database`` connection and the ``GraphRunner`` (which owns the compiled graph
and checkpointer). Both are created at app startup and reused per request.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.config import get_settings
from app.db.connection import Database
from app.graph.runner import GraphRunner


@dataclass
class AppContext:
    """Container for shared, long-lived application resources."""

    db: Database
    runner: GraphRunner


_context: AppContext | None = None


def init_context() -> AppContext:
    """Create the shared context (called once at startup)."""
    global _context
    settings = get_settings()
    settings.ensure_data_dirs()
    db = Database(settings.business_db_path)
    runner = GraphRunner(db)
    _context = AppContext(db=db, runner=runner)
    return _context


def shutdown_context() -> None:
    """Tear down shared resources (called at shutdown)."""
    global _context
    if _context is not None:
        _context.runner.close()
        _context.db.close()
        _context = None


def get_context() -> AppContext:
    if _context is None:
        return init_context()
    return _context


def get_db() -> Database:
    return get_context().db


def get_runner() -> GraphRunner:
    return get_context().runner
