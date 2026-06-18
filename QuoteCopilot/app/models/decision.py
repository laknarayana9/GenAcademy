"""Decision models: reason codes, citations, and the final decision packet.

These mirror the `decision_packets` table and are the underwriter-facing
output of the packaging subgraph.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Recommendation(str, Enum):
    """Final underwriting recommendation."""

    ACCEPT = "ACCEPT"
    REFER = "REFER"
    DECLINE = "DECLINE"


class ReviewStatus(str, Enum):
    """Whether the packet is auto-final or awaiting/done with human review."""

    AUTO_FINAL = "auto_final"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReasonCode(BaseModel):
    """A single governed reason supporting the recommendation."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="Stable identifier, e.g. RC-001")
    description: str
    severity: str = Field(default="info", description="info|refer|knockout")


class Citation(BaseModel):
    """A traceable reference to a retrieved guideline chunk."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    source: str = Field(..., description="Source file or doc id")
    section: str | None = None
    text: str


class DecisionPacket(BaseModel):
    """The structured, cited output for a completed run."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    recommendation: Recommendation
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    facts_used: dict = Field(default_factory=dict)
    premium_indication: float | None = None
    next_steps: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = ReviewStatus.AUTO_FINAL
