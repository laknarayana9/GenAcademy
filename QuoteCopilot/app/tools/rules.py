"""Deterministic HO3 eligibility and referral rule engine.

This module is the governed source of truth for underwriting decisions. It
contains no LLM calls and must never be overridden by model output. Agents may
phrase rationale around these findings but cannot change them.

The engine evaluates a canonical submission (plus optional enrichment hazard
signals) and returns structured findings: a list of reason codes, the strongest
preliminary decision, the facts that drove it, and a confidence score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.submission import HO3CanonicalSubmission, OccupancyType, RoofType

# Severity ordering: higher value wins when aggregating to a decision.
_SEVERITY_RANK = {"info": 0, "refer": 1, "knockout": 2}
_SEVERITY_TO_DECISION = {"info": "ACCEPT", "refer": "REFER", "knockout": "DECLINE"}

# --- Threshold constants (synthetic guideline values) ----------------------
MAX_ROOF_AGE_ACCEPT = 20          # roof older than this refers
KNOCKOUT_ROOF_AGE = 30            # roof older than this declines
MIN_YEAR_BUILT_REFER = 1950       # built before this refers (old wiring/plumbing)
MAX_DWELLING_AMOUNT = 2_000_000   # above this refers (high-value)
MIN_DWELLING_AMOUNT = 75_000      # below this refers (rebuild cost mismatch)
WILDFIRE_REFER_BANDS = {"high", "very_high"}
CLAIMS_REFER_COUNT = 2            # this many or more prior claims refers
CLAIMS_KNOCKOUT_COUNT = 4


@dataclass
class RuleFinding:
    """A single triggered (or passing) rule outcome."""

    code: str
    description: str
    severity: str  # info|refer|knockout
    facts: dict = field(default_factory=dict)


@dataclass
class RuleResult:
    """Aggregate output of the rule engine for one submission."""

    preliminary_decision: str          # ACCEPT|REFER|DECLINE
    reason_codes: list[RuleFinding]
    facts_used: dict
    confidence: float

    def as_dict(self) -> dict:
        return {
            "preliminary_decision": self.preliminary_decision,
            "reason_codes": [
                {
                    "code": f.code,
                    "description": f.description,
                    "severity": f.severity,
                    "facts": f.facts,
                }
                for f in self.reason_codes
            ],
            "facts_used": self.facts_used,
            "confidence": self.confidence,
        }


def _hazard_band(enrichment: dict | None, key: str) -> str | None:
    """Safely read a hazard band from the enrichment hazard profile."""
    if not enrichment:
        return None
    hazard = enrichment.get("hazard_profile", {}) or {}
    value = hazard.get(key)
    return value.lower() if isinstance(value, str) else None


def evaluate(
    submission: HO3CanonicalSubmission, enrichment: dict | None = None
) -> RuleResult:
    """Evaluate eligibility/referral rules against a canonical submission.

    Parameters
    ----------
    submission:
        Validated canonical HO3 submission.
    enrichment:
        Optional enrichment dict carrying a ``hazard_profile`` with bands such
        as ``wildfire_band`` and ``flood_zone``.
    """
    findings: list[RuleFinding] = []
    facts: dict = {}

    # --- Occupancy knockouts ------------------------------------------
    if submission.occupancy == OccupancyType.VACANT:
        findings.append(
            RuleFinding(
                "RC-101",
                "Vacant dwellings are ineligible for HO3.",
                "knockout",
                {"occupancy": submission.occupancy.value},
            )
        )
    elif submission.occupancy == OccupancyType.RENTAL:
        findings.append(
            RuleFinding(
                "RC-102",
                "Rental occupancy requires referral to a different product.",
                "refer",
                {"occupancy": submission.occupancy.value},
            )
        )

    # --- Roof age ------------------------------------------------------
    if submission.roof_age_years is not None:
        facts["roof_age_years"] = submission.roof_age_years
        if submission.roof_age_years > KNOCKOUT_ROOF_AGE:
            findings.append(
                RuleFinding(
                    "RC-201",
                    f"Roof age {submission.roof_age_years} exceeds maximum "
                    f"{KNOCKOUT_ROOF_AGE} years.",
                    "knockout",
                    {"roof_age_years": submission.roof_age_years},
                )
            )
        elif submission.roof_age_years > MAX_ROOF_AGE_ACCEPT:
            findings.append(
                RuleFinding(
                    "RC-202",
                    f"Roof age {submission.roof_age_years} exceeds "
                    f"{MAX_ROOF_AGE_ACCEPT} years; refer for inspection.",
                    "refer",
                    {"roof_age_years": submission.roof_age_years},
                )
            )

    # --- Roof type -----------------------------------------------------
    if submission.roof_type == RoofType.WOOD_SHAKE:
        findings.append(
            RuleFinding(
                "RC-203",
                "Wood shake roofs refer due to wildfire/ember exposure.",
                "refer",
                {"roof_type": submission.roof_type.value},
            )
        )

    # --- Dwelling age --------------------------------------------------
    facts["year_built"] = submission.year_built
    if submission.year_built < MIN_YEAR_BUILT_REFER:
        findings.append(
            RuleFinding(
                "RC-301",
                f"Built before {MIN_YEAR_BUILT_REFER}; refer for systems update "
                "verification.",
                "refer",
                {"year_built": submission.year_built},
            )
        )

    # --- Coverage amount -----------------------------------------------
    dwelling = submission.coverage.dwelling_amount
    facts["dwelling_amount"] = dwelling
    if dwelling > MAX_DWELLING_AMOUNT:
        findings.append(
            RuleFinding(
                "RC-401",
                f"Dwelling amount {dwelling:.0f} exceeds high-value threshold "
                f"{MAX_DWELLING_AMOUNT}.",
                "refer",
                {"dwelling_amount": dwelling},
            )
        )
    elif dwelling < MIN_DWELLING_AMOUNT:
        findings.append(
            RuleFinding(
                "RC-402",
                f"Dwelling amount {dwelling:.0f} below minimum insurable "
                f"{MIN_DWELLING_AMOUNT}.",
                "refer",
                {"dwelling_amount": dwelling},
            )
        )

    # --- Claims history ------------------------------------------------
    claim_count = len(submission.prior_claims)
    facts["prior_claim_count"] = claim_count
    if claim_count >= CLAIMS_KNOCKOUT_COUNT:
        findings.append(
            RuleFinding(
                "RC-501",
                f"{claim_count} prior claims exceeds maximum "
                f"{CLAIMS_KNOCKOUT_COUNT - 1}.",
                "knockout",
                {"prior_claim_count": claim_count},
            )
        )
    elif claim_count >= CLAIMS_REFER_COUNT:
        findings.append(
            RuleFinding(
                "RC-502",
                f"{claim_count} prior claims; refer for loss-history review.",
                "refer",
                {"prior_claim_count": claim_count},
            )
        )

    # --- Hazard bands (from enrichment) --------------------------------
    wildfire_band = _hazard_band(enrichment, "wildfire_band")
    if wildfire_band:
        facts["wildfire_band"] = wildfire_band
        if wildfire_band in WILDFIRE_REFER_BANDS and not submission.wildfire_mitigation:
            findings.append(
                RuleFinding(
                    "RC-601",
                    f"Wildfire band '{wildfire_band}' without mitigation; refer.",
                    "refer",
                    {"wildfire_band": wildfire_band, "mitigation": False},
                )
            )

    flood_zone = _hazard_band(enrichment, "flood_zone")
    if flood_zone:
        facts["flood_zone"] = flood_zone
        if flood_zone in {"a", "v", "ae", "ve"}:
            findings.append(
                RuleFinding(
                    "RC-701",
                    f"Special flood hazard area '{flood_zone}'; refer.",
                    "refer",
                    {"flood_zone": flood_zone},
                )
            )

    # --- Liability -----------------------------------------------------
    liability = submission.coverage.liability_limit
    if liability is not None and liability > 1_000_000:
        findings.append(
            RuleFinding(
                "RC-801",
                f"Liability limit {liability:.0f} above standard; refer.",
                "refer",
                {"liability_limit": liability},
            )
        )

    return _aggregate(findings, facts)


def _aggregate(findings: list[RuleFinding], facts: dict) -> RuleResult:
    """Combine findings into a single decision and confidence."""
    if not findings:
        accept = RuleFinding(
            "RC-001",
            "All evaluated eligibility and referral rules passed.",
            "info",
            {},
        )
        return RuleResult("ACCEPT", [accept], facts, confidence=0.95)

    top_severity = max(_SEVERITY_RANK[f.severity] for f in findings)
    decision = _SEVERITY_TO_DECISION[
        next(k for k, v in _SEVERITY_RANK.items() if v == top_severity)
    ]

    # Confidence: deterministic rules are certain; multiple borderline refers
    # lower confidence slightly to encourage human review framing.
    if decision == "DECLINE":
        confidence = 0.97
    elif decision == "REFER":
        confidence = max(0.6, 0.9 - 0.05 * (len(findings) - 1))
    else:
        confidence = 0.95

    return RuleResult(decision, findings, facts, confidence=round(confidence, 2))
