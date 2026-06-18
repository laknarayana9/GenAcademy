"""Deterministic premium indication calculator.

Pure, documented rating logic — no LLM calls. Produces an indicative annual
premium and the multiplicative factors used to derive it, so the decision
packet can show a transparent rating breakdown. Values are synthetic and for
demonstration only.

If a required rating input is missing and no documented default applies, the
caller (assessment subgraph) routes to review rather than guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.submission import (
    ConstructionType,
    HO3CanonicalSubmission,
    RoofType,
)

# --- Base rate and documented factor tables (synthetic) --------------------
BASE_RATE_PER_1000 = 4.50  # USD premium per $1,000 of dwelling coverage

CONSTRUCTION_FACTORS = {
    ConstructionType.FRAME: 1.15,
    ConstructionType.MASONRY: 0.95,
    ConstructionType.MASONRY_VENEER: 1.00,
    ConstructionType.FIRE_RESISTIVE: 0.85,
    ConstructionType.MANUFACTURED: 1.35,
}

ROOF_FACTORS = {
    RoofType.ASPHALT_SHINGLE: 1.00,
    RoofType.METAL: 0.92,
    RoofType.TILE: 0.95,
    RoofType.WOOD_SHAKE: 1.40,
    RoofType.FLAT_BUILT_UP: 1.10,
}

# Deductible credit: higher deductible lowers premium.
DEDUCTIBLE_FACTORS = {
    500: 1.10,
    1000: 1.00,
    2500: 0.90,
    5000: 0.82,
}
DEFAULT_DEDUCTIBLE_FACTOR = 1.00

WILDFIRE_BAND_FACTORS = {
    "low": 1.00,
    "moderate": 1.10,
    "high": 1.30,
    "very_high": 1.60,
}
WILDFIRE_MITIGATION_CREDIT = 0.90  # applied when mitigation present


@dataclass
class RatingResult:
    """Premium indication plus the factors that produced it."""

    premium_indication: float
    rating_factors: dict
    incomplete: bool = False
    missing_inputs: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "premium_indication": self.premium_indication,
            "rating_factors": self.rating_factors,
            "incomplete": self.incomplete,
            "missing_inputs": self.missing_inputs,
        }


def _roof_age_factor(roof_age_years: int | None) -> tuple[float, bool]:
    """Return (factor, used_default). Older roofs cost more; default if unknown."""
    if roof_age_years is None:
        return 1.05, True  # documented neutral-ish default
    if roof_age_years <= 5:
        return 0.95, False
    if roof_age_years <= 15:
        return 1.00, False
    if roof_age_years <= 25:
        return 1.20, False
    return 1.45, False


def _deductible_factor(deductible: float) -> float:
    """Nearest documented deductible tier factor."""
    if deductible in DEDUCTIBLE_FACTORS:
        return DEDUCTIBLE_FACTORS[deductible]
    nearest = min(DEDUCTIBLE_FACTORS, key=lambda d: abs(d - deductible))
    return DEDUCTIBLE_FACTORS[nearest]


def calculate(
    submission: HO3CanonicalSubmission, enrichment: dict | None = None
) -> RatingResult:
    """Compute an indicative annual premium from the submission and hazards."""
    missing: list[str] = []
    factors: dict = {}

    dwelling = submission.coverage.dwelling_amount
    base_premium = (dwelling / 1000.0) * BASE_RATE_PER_1000
    factors["base_premium"] = round(base_premium, 2)

    construction_factor = CONSTRUCTION_FACTORS.get(submission.construction_type, 1.0)
    factors["construction"] = construction_factor

    roof_factor = ROOF_FACTORS.get(submission.roof_type, 1.0)
    factors["roof_type"] = roof_factor

    roof_age_factor, used_default = _roof_age_factor(submission.roof_age_years)
    factors["roof_age"] = roof_age_factor
    if used_default:
        missing.append("roof_age_years")

    deductible_factor = _deductible_factor(submission.coverage.deductible)
    factors["deductible"] = deductible_factor

    # Wildfire band from enrichment (optional).
    wildfire_factor = 1.0
    band = None
    if enrichment:
        hazard = enrichment.get("hazard_profile", {}) or {}
        band = hazard.get("wildfire_band")
        if isinstance(band, str):
            wildfire_factor = WILDFIRE_BAND_FACTORS.get(band.lower(), 1.0)
    factors["wildfire_band"] = wildfire_factor
    if submission.wildfire_mitigation:
        wildfire_factor *= WILDFIRE_MITIGATION_CREDIT
        factors["wildfire_mitigation_credit"] = WILDFIRE_MITIGATION_CREDIT

    premium = (
        base_premium
        * construction_factor
        * roof_factor
        * roof_age_factor
        * deductible_factor
        * wildfire_factor
    )

    return RatingResult(
        premium_indication=round(premium, 2),
        rating_factors=factors,
        incomplete=bool(missing),
        missing_inputs=missing,
    )
