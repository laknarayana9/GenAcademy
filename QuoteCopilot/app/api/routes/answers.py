"""Answer resume route.

Validates supplied answers against the required_questions stored for a paused
run, then resumes the graph on the same thread_id. Returns the updated run
status (which may be completed, pending_review, or waiting_for_info if a further
follow-up is needed).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.deps import get_db, get_runner
from app.db.connection import Database
from app.graph.runner import GraphRunner

router = APIRouter(prefix="/runs", tags=["runs"])


class AnswerSubmission(BaseModel):
    """Body for POST /runs/{run_id}/answers."""

    model_config = ConfigDict(extra="forbid")

    answers: dict[str, Any]


def _run_error(status_code: int, message: str, run_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": message, "run_id": run_id}
    )


@router.post("/{run_id}/answers")
async def submit_answers(
    run_id: str,
    body: AnswerSubmission,
    runner: GraphRunner = Depends(get_runner),
    db: Database = Depends(get_db),
):
    """Resume a paused run with missing-info answers."""
    run = db.get_run(run_id)
    if not run:
        return _run_error(404, "Run not found", run_id)
    if run["status"] != "waiting_for_info":
        return _run_error(409, "Run is not waiting for information", run_id)

    required = db.get_pending_questions(run_id)
    required_fields = {q["field"] for q in required}
    missing = sorted(f for f in required_fields if f not in body.answers)
    if missing:
        return JSONResponse(
            status_code=422,
            content={
                "error": "Missing required answers",
                "field_errors": [{"field": f, "msg": "required"} for f in missing],
            },
        )

    result = runner.resume(run_id, body.answers)
    return {"run_id": run_id, "status": result.get("status")}
