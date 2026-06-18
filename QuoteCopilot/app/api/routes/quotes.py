"""Quote intake routes.

Both endpoints generate a run_id, write a processing run row, kick off graph
execution in the background, and return ``{run_id, status}`` immediately. The
client polls ``GET /runs/{run_id}`` for completion or follow-up questions.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends

from app.api.deps import get_db, get_runner
from app.db.connection import Database
from app.graph.runner import GraphRunner
from app.models.submission import HO3CanonicalSubmission, LegacyQuotePayload

router = APIRouter(prefix="/quote", tags=["quote"])


def _kickoff(
    runner: GraphRunner,
    db: Database,
    raw: dict,
    quote_id: str,
    bg: BackgroundTasks,
) -> dict:
    run_id = str(uuid.uuid4())
    db.create_run(run_id, quote_id, "processing")
    bg.add_task(runner.start, run_id, quote_id, raw)
    return {"run_id": run_id, "status": "processing"}


@router.post("/ho3")
async def start_ho3(
    submission: HO3CanonicalSubmission,
    background_tasks: BackgroundTasks,
    runner: GraphRunner = Depends(get_runner),
    db: Database = Depends(get_db),
) -> dict:
    """Start a canonical HO3 underwriting run."""
    raw = submission.model_dump(mode="json")
    return _kickoff(runner, db, raw, submission.quote_id, background_tasks)


@router.post("/run")
async def start_legacy(
    payload: LegacyQuotePayload,
    background_tasks: BackgroundTasks,
    runner: GraphRunner = Depends(get_runner),
    db: Database = Depends(get_db),
) -> dict:
    """Start a legacy producer-payload underwriting run."""
    raw = payload.model_dump(mode="json")
    quote_id = payload.quote_id or str(uuid.uuid4())
    return _kickoff(runner, db, raw, quote_id, background_tasks)
