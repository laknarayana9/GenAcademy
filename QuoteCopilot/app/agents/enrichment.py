"""Enrichment agent.

Adds deterministic external-style context (wildfire band, flood zone, territory)
and produces a retrieval plan. Detects the contextual wildfire-mitigation gap
that requires a follow-up pause. All signals are deterministic and explainable;
real hazard APIs could later be swapped in behind the same boundary.
"""

from __future__ import annotations

from app.graph.state import RunState, audit

NODE = "enrich"

# Synthetic state-level wildfire exposure table.
_HIGH_WILDFIRE_STATES = {"CA", "CO", "OR", "WA", "AZ", "NM", "MT", "ID", "UT"}
_VERY_HIGH_WILDFIRE_STATES = {"CA"}


def _wildfire_band(canonical: dict) -> str:
    state = (canonical.get("state") or "").upper()
    if state in _VERY_HIGH_WILDFIRE_STATES:
        return "very_high"
    if state in _HIGH_WILDFIRE_STATES:
        return "high"
    return "low"


def _flood_zone(canonical: dict) -> str:
    distance = canonical.get("distance_to_coast_miles")
    if distance is None:
        return "X"
    if distance < 0.5:
        return "VE"
    if distance < 3:
        return "AE"
    return "X"


def _territory(canonical: dict) -> str:
    zip_code = str(canonical.get("zip_code") or "00000")
    return f"T{zip_code[:2]}"


def _retrieval_plan(canonical: dict, hazard: dict) -> dict:
    queries = [
        {
            "intent": "HO3 general eligibility and decision aggregation",
            "keywords": ["eligibility", "referral", "knockout", "HO3"],
        },
        {
            "intent": "occupancy eligibility",
            "keywords": ["occupancy", canonical.get("occupancy", ""), "eligible"],
        },
        {
            "intent": "roof age and covering thresholds",
            "keywords": ["roof age", "referral", "wood shake", "knockout"],
        },
    ]
    if hazard.get("wildfire_band") in {"high", "very_high"}:
        queries.append(
            {
                "intent": "wildfire band eligibility and mitigation",
                "keywords": ["wildfire", "band", "mitigation", "RC-601"],
            }
        )
    if hazard.get("flood_zone") in {"A", "AE", "V", "VE"}:
        queries.append(
            {
                "intent": "flood zone referral",
                "keywords": ["flood", "zone", "special flood hazard", "RC-701"],
            }
        )
    if canonical.get("prior_claim_count", len(canonical.get("prior_claims", []))) >= 2:
        queries.append(
            {
                "intent": "claims history referral",
                "keywords": ["claims", "loss history", "referral", "RC-502"],
            }
        )
    return {"queries": queries}


def enrich(state: RunState) -> dict:
    """Produce property/hazard profiles and a retrieval plan."""
    canonical = state.get("submission_canonical", {}) or {}
    answers = state.get("additional_answers", {}) or {}

    hazard = {
        "wildfire_band": _wildfire_band(canonical),
        "flood_zone": _flood_zone(canonical),
    }
    property_profile = {
        "territory": _territory(canonical),
        "construction_type": canonical.get("construction_type"),
        "year_built": canonical.get("year_built"),
    }

    # Contextual wildfire mitigation follow-up.
    mitigation = canonical.get("wildfire_mitigation")
    if "wildfire_mitigation" in answers:
        mitigation = answers["wildfire_mitigation"]
    needs_mitigation_info = (
        hazard["wildfire_band"] in {"high", "very_high"} and mitigation is None
    )

    enrichment = {
        "property_profile": property_profile,
        "hazard_profile": hazard,
        "retrieval_plan": _retrieval_plan(canonical, hazard),
    }

    if needs_mitigation_info:
        return {
            "current_node": NODE,
            "status": "waiting_for_info",
            "enrichment": enrichment,
            "missing_info": ["wildfire_mitigation"],
            "required_questions": [
                {
                    "field": "wildfire_mitigation",
                    "question": (
                        "This property is in a high wildfire area. Is qualifying "
                        "mitigation (defensible space and hardened construction) "
                        "present? (true/false)"
                    ),
                    "type": "boolean",
                }
            ],
            "events": [
                audit(NODE, "paused", {"reason": "wildfire_mitigation_required"}),
            ],
        }

    return {
        "current_node": NODE,
        "status": "processing",
        "enrichment": enrichment,
        "missing_info": [],
        "required_questions": [],
        "events": [audit(NODE, "completed", {"hazard": hazard})],
    }
