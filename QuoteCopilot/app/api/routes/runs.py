"""Run inspection routes: list, detail (state + packet), and audit trail."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_db
from app.db.connection import Database

router = APIRouter(prefix="/runs", tags=["runs"])


def _not_found(run_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=404, content={"error": "Run not found", "run_id": run_id}
    )


@router.get("")
async def list_runs(limit: int = 50, db: Database = Depends(get_db)) -> dict:
    """List recent runs, newest first."""
    return {"runs": db.list_runs(limit=limit)}


@router.get("/{run_id}")
async def get_run(run_id: str, db: Database = Depends(get_db)):
    """Return run state, decision packet, and any pending questions."""
    run = db.get_run(run_id)
    if not run:
        return _not_found(run_id)
    return {
        "run": run,
        "decision_packet": db.get_decision_packet(run_id),
        "required_questions": db.get_pending_questions(run_id),
        "review_task": db.get_review_task(run_id),
    }


@router.get("/{run_id}/audit")
async def get_audit(run_id: str, db: Database = Depends(get_db)):
    """Return the node-by-node audit trail for a run."""
    run = db.get_run(run_id)
    if not run:
        return _not_found(run_id)
    return {"run_id": run_id, "events": db.get_audit_events(run_id)}
