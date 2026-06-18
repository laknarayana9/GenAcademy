"""Review models: human-in-the-loop tasks and reviewer actions.

`ReviewTask` mirrors the `review_tasks` table. `ReviewActionRequest` is the
body accepted at `POST /reviews/{run_id}/actions`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ReviewTaskStatus(str, Enum):
    """Lifecycle of a review task."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    INFO_REQUESTED = "info_requested"
    CLOSED = "closed"


class ReviewPriority(str, Enum):
    """Triage priority for the review queue."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ReviewTrigger(str, Enum):
    """Why the run was routed to human review."""

    MISSING_INFO = "missing_info"
    REFER = "refer"
    DECLINE = "decline"
    VERIFICATION_FAILURE = "verification_failure"


class ReviewAction(str, Enum):
    """Action a reviewer can take on a task."""

    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_INFO = "request_info"
    CLOSE = "close"


class ReviewActionRequest(BaseModel):
    """Body for POST /reviews/{run_id}/actions."""

    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    note: str = Field(default="", description="Optional reviewer rationale")


class ReviewTask(BaseModel):
    """A human review task attached to a run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: ReviewTaskStatus = ReviewTaskStatus.PENDING
    priority: ReviewPriority = ReviewPriority.MEDIUM
    trigger: ReviewTrigger
    review_packet: dict = Field(default_factory=dict)
    reviewer_note: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
