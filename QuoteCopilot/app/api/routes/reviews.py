"""Human-in-the-loop review routes.

Lists pending review tasks, returns a full review packet, and applies reviewer
actions. Actions update both the review task and the run status. Approving a
REFER finalizes the decision packet and completes the run.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import get_db
from app.db.connection import Database
from app.models.decision import ReviewStatus
from app.models.review import (
    ReviewAction,
    ReviewActionRequest,
    ReviewTaskStatus,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])

# Map a reviewer action to (review_task_status, run_status, packet_review_status)
_ACTION_MAP = {
    ReviewAction.APPROVE: (
        ReviewTaskStatus.APPROVED,
        "completed",
        ReviewStatus.APPROVED,
    ),
    ReviewAction.REJECT: (
        ReviewTaskStatus.REJECTED,
        "completed",
        ReviewStatus.REJECTED,
    ),
    ReviewAction.REQUEST_INFO: (
        ReviewTaskStatus.INFO_REQUESTED,
        "waiting_for_info",
        None,
    ),
    ReviewAction.CLOSE: (ReviewTaskStatus.CLOSED, "completed", None),
}


@router.get("/pending")
async def pending_reviews(db: Database = Depends(get_db)) -> dict:
    """List open review tasks, highest priority first."""
    return {"reviews": db.list_pending_reviews()}


@router.get("/{run_id}")
async def get_review(run_id: str, db: Database = Depends(get_db)):
    """Return the full review packet for a run."""
    task = db.get_review_task(run_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"error": "Review task not found", "run_id": run_id},
        )
    return {
        "review_task": task,
        "decision_packet": db.get_decision_packet(run_id),
        "run": db.get_run(run_id),
    }


@router.post("/{run_id}/actions")
async def apply_action(
    run_id: str,
    body: ReviewActionRequest,
    db: Database = Depends(get_db),
):
    """Apply approve / reject / request_info / close to a review task."""
    task = db.get_review_task(run_id)
    if not task:
        return JSONResponse(
            status_code=404,
            content={"error": "Review task not found", "run_id": run_id},
        )

    task_status, run_status, packet_status = _ACTION_MAP[body.action]
    db.update_review_task(run_id, task_status.value, body.note or None)
    db.update_run_status(run_id, run_status)

    # Finalize the decision packet's review status when applicable.
    if packet_status is not None:
        packet = db.get_decision_packet(run_id)
        if packet:
            packet["review_status"] = packet_status.value
            db.upsert_decision_packet(run_id, packet)

    db.add_audit_event(
        run_id,
        "review",
        "resolved",
        {"action": body.action.value, "note": body.note},
    )

    return {
        "run_id": run_id,
        "review_status": task_status.value,
        "status": run_status,
    }
