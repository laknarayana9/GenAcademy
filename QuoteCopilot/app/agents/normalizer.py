"""Intake Normalizer agent.

Converts a raw payload (canonical HO3 or legacy producer shape) into a canonical
submission, merges any answers supplied during resume, and detects required
follow-up facts. Pure function over RunState: returns a partial state update.

Determinism note: field mapping and missing-info detection are fully
deterministic. The LLM is used only to phrase follow-up questions, with a
deterministic fallback, so it can never invent or suppress a required fact.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.graph.state import RunState, audit
from app.llm.factory import complete_text
from app.models.submission import (
    ClaimRecord,
    ConstructionType,
    CoverageRequest,
    HO3CanonicalSubmission,
    OccupancyType,
    RoofType,
)

NODE = "normalize"

# Facts that must be present (with a real value) before assessment can run.
FOLLOWUP_FIELDS = {
    "roof_age_years": "What is the age of the roof in years?",
    "occupancy": "How is the dwelling occupied (owner-primary, owner-secondary, seasonal, rental, vacant)?",
}

_CONSTRUCTION_ALIASES = {
    "frame": ConstructionType.FRAME,
    "wood": ConstructionType.FRAME,
    "masonry": ConstructionType.MASONRY,
    "brick": ConstructionType.MASONRY,
    "masonry_veneer": ConstructionType.MASONRY_VENEER,
    "veneer": ConstructionType.MASONRY_VENEER,
    "fire_resistive": ConstructionType.FIRE_RESISTIVE,
    "concrete": ConstructionType.FIRE_RESISTIVE,
    "manufactured": ConstructionType.MANUFACTURED,
    "mobile": ConstructionType.MANUFACTURED,
}

_ROOF_ALIASES = {
    "asphalt": RoofType.ASPHALT_SHINGLE,
    "asphalt_shingle": RoofType.ASPHALT_SHINGLE,
    "shingle": RoofType.ASPHALT_SHINGLE,
    "metal": RoofType.METAL,
    "tile": RoofType.TILE,
    "wood_shake": RoofType.WOOD_SHAKE,
    "shake": RoofType.WOOD_SHAKE,
    "flat": RoofType.FLAT_BUILT_UP,
    "flat_built_up": RoofType.FLAT_BUILT_UP,
}

_OCCUPANCY_ALIASES = {
    "owner": OccupancyType.OWNER_PRIMARY,
    "owner_primary": OccupancyType.OWNER_PRIMARY,
    "primary": OccupancyType.OWNER_PRIMARY,
    "owner_secondary": OccupancyType.OWNER_SECONDARY,
    "secondary": OccupancyType.OWNER_SECONDARY,
    "seasonal": OccupancyType.SEASONAL,
    "rental": OccupancyType.RENTAL,
    "tenant": OccupancyType.RENTAL,
    "vacant": OccupancyType.VACANT,
}


def _coerce_enum(value, aliases):
    if value is None:
        return None
    key = str(value).strip().lower().replace(" ", "_")
    return aliases.get(key)


def _candidate_fields(raw: dict) -> dict:
    """Map either a canonical or legacy payload into a single flat candidate."""
    # Canonical shape already uses these keys; legacy uses alternates.
    return {
        "quote_id": raw.get("quote_id"),
        "applicant_name": raw.get("applicant_name") or raw.get("name"),
        "state": raw.get("state") or raw.get("address_state"),
        "zip_code": raw.get("zip_code") or raw.get("zip"),
        "year_built": raw.get("year_built"),
        "construction_type": _coerce_enum(
            raw.get("construction_type") or raw.get("construction"),
            _CONSTRUCTION_ALIASES,
        ),
        "roof_type": _coerce_enum(
            raw.get("roof_type") or raw.get("roof"), _ROOF_ALIASES
        ),
        "roof_age_years": raw.get("roof_age_years")
        if raw.get("roof_age_years") is not None
        else raw.get("roof_age"),
        "square_feet": raw.get("square_feet") or raw.get("sq_ft"),
        "stories": raw.get("stories", 1),
        "occupancy": _coerce_enum(
            raw.get("occupancy") or raw.get("use"), _OCCUPANCY_ALIASES
        ),
        "coverage": _candidate_coverage(raw),
        "prior_claims": _candidate_claims(raw),
        "wildfire_mitigation": raw.get("wildfire_mitigation"),
        "distance_to_coast_miles": raw.get("distance_to_coast_miles"),
    }


def _candidate_coverage(raw: dict) -> dict:
    coverage = raw.get("coverage")
    if isinstance(coverage, dict):
        return coverage
    return {
        "dwelling_amount": raw.get("coverage_a"),
        "deductible": raw.get("deductible"),
        "liability_limit": raw.get("liability"),
    }


def _candidate_claims(raw: dict) -> list:
    claims = raw.get("prior_claims") or raw.get("claims") or []
    normalized = []
    for c in claims:
        if isinstance(c, dict):
            normalized.append(
                {
                    "year": c.get("year", 2000),
                    "peril": c.get("peril", "unknown"),
                    "amount": c.get("amount", 0),
                }
            )
    return normalized


def _question(field: str) -> dict:
    return {
        "field": field,
        "question": FOLLOWUP_FIELDS.get(field, f"Please provide {field}."),
        "type": "text",
    }


def normalize(state: RunState) -> dict:
    """Normalize intake and detect required follow-up facts."""
    raw = dict(state.get("submission_raw", {}))
    answers = state.get("additional_answers", {}) or {}

    candidate = _candidate_fields(raw)
    # Merge resume answers (override candidate fields).
    for key, value in answers.items():
        if key == "occupancy":
            value = _coerce_enum(value, _OCCUPANCY_ALIASES) or value
        candidate[key] = value

    missing: list[str] = []
    questions: list[dict] = []

    # Hard-required structural fields needed to build the canonical model.
    for field in (
        "state",
        "zip_code",
        "year_built",
        "construction_type",
        "roof_type",
        "square_feet",
    ):
        if candidate.get(field) in (None, ""):
            missing.append(field)
            questions.append(_question(field))

    cov = candidate.get("coverage") or {}
    if cov.get("dwelling_amount") in (None, "") or cov.get("deductible") in (None, ""):
        missing.append("coverage")
        questions.append(
            {
                "field": "coverage",
                "question": "Provide dwelling amount (Coverage A) and deductible.",
                "type": "object",
            }
        )

    # Follow-up facts required for a sound assessment.
    for field in FOLLOWUP_FIELDS:
        if candidate.get(field) in (None, ""):
            missing.append(field)
            questions.append(_question(field))

    if missing:
        questions = _phrase_questions(questions)
        return {
            "current_node": NODE,
            "status": "waiting_for_info",
            "submission_canonical": _safe_partial(candidate),
            "missing_info": missing,
            "required_questions": questions,
            "events": [
                audit(NODE, "paused", {"missing_info": missing}),
            ],
        }

    # All present: build the validated canonical submission.
    try:
        submission = HO3CanonicalSubmission(
            quote_id=candidate["quote_id"] or state.get("quote_id", "unknown"),
            applicant_name=candidate["applicant_name"] or "Unknown Applicant",
            state=str(candidate["state"]).upper()[:2],
            zip_code=str(candidate["zip_code"]),
            year_built=int(candidate["year_built"]),
            construction_type=candidate["construction_type"],
            roof_type=candidate["roof_type"],
            roof_age_years=int(candidate["roof_age_years"]),
            square_feet=int(candidate["square_feet"]),
            stories=int(candidate.get("stories", 1) or 1),
            occupancy=candidate["occupancy"],
            coverage=CoverageRequest(**cov),
            prior_claims=[ClaimRecord(**c) for c in candidate["prior_claims"]],
            wildfire_mitigation=candidate.get("wildfire_mitigation"),
            distance_to_coast_miles=candidate.get("distance_to_coast_miles"),
        )
    except (ValidationError, ValueError, TypeError) as exc:
        return {
            "current_node": NODE,
            "status": "failed",
            "events": [audit(NODE, "failed", {"error": str(exc)})],
        }

    return {
        "current_node": NODE,
        "status": "processing",
        "submission_canonical": submission.model_dump(mode="json"),
        "missing_info": [],
        "required_questions": [],
        "events": [audit(NODE, "completed", {"quote_id": submission.quote_id})],
    }


def _safe_partial(candidate: dict) -> dict:
    """Serialize whatever fields we already have for display while paused."""
    out = {}
    for k, v in candidate.items():
        if hasattr(v, "value"):
            out[k] = v.value
        else:
            out[k] = v
    return out


def _phrase_questions(questions: list[dict]) -> list[dict]:
    """Optionally improve question wording via LLM; deterministic fallback."""
    fields = ", ".join(q["field"] for q in questions)
    system = (
        "You are an insurance intake assistant. Rewrite each underwriting "
        "follow-up question to be clear and polite. Keep one line per question."
    )
    user = "Fields needing questions: " + fields
    fallback = "\n".join(q["question"] for q in questions)
    improved = complete_text("normalizer", system, user, fallback)
    lines = [ln.strip("-• ").strip() for ln in improved.splitlines() if ln.strip()]
    if len(lines) == len(questions):
        for q, line in zip(questions, lines):
            q["question"] = line
    return questions
