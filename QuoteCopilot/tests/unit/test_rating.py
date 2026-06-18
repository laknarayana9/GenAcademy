"""Unit tests for the deterministic rating tool."""

from __future__ import annotations

from app.models.submission import (
    ConstructionType,
    CoverageRequest,
    HO3CanonicalSubmission,
    OccupancyType,
    RoofType,
)
from app.tools import rating


def _submission(**overrides) -> HO3CanonicalSubmission:
    base = dict(
        quote_id="q",
        applicant_name="A",
        state="TX",
        zip_code="75001",
        year_built=2010,
        construction_type=ConstructionType.MASONRY,
        roof_type=RoofType.METAL,
        roof_age_years=5,
        square_feet=2000,
        occupancy=OccupancyType.OWNER_PRIMARY,
        coverage=CoverageRequest(dwelling_amount=400000, deductible=1000),
    )
    base.update(overrides)
    return HO3CanonicalSubmission(**base)


def test_premium_is_positive():
    result = rating.calculate(_submission())
    assert result.premium_indication > 0
    assert "base_premium" in result.rating_factors


def test_missing_roof_age_uses_default_and_flags():
    result = rating.calculate(_submission(roof_age_years=None))
    assert result.incomplete is True
    assert "roof_age_years" in result.missing_inputs


def test_wildfire_band_increases_premium():
    low = rating.calculate(_submission(), {"hazard_profile": {"wildfire_band": "low"}})
    high = rating.calculate(
        _submission(), {"hazard_profile": {"wildfire_band": "very_high"}}
    )
    assert high.premium_indication > low.premium_indication


def test_mitigation_credit_lowers_premium():
    no_mit = rating.calculate(
        _submission(wildfire_mitigation=False),
        {"hazard_profile": {"wildfire_band": "high"}},
    )
    with_mit = rating.calculate(
        _submission(wildfire_mitigation=True),
        {"hazard_profile": {"wildfire_band": "high"}},
    )
    assert with_mit.premium_indication < no_mit.premium_indication
