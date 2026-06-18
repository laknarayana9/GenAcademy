"""Unit tests for the deterministic rule engine."""

from __future__ import annotations

from app.models.submission import (
    ConstructionType,
    CoverageRequest,
    HO3CanonicalSubmission,
    OccupancyType,
    RoofType,
)
from app.tools import rules


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


def test_clean_submission_accepts():
    result = rules.evaluate(_submission())
    assert result.preliminary_decision == "ACCEPT"
    assert [f.code for f in result.reason_codes] == ["RC-001"]


def test_old_roof_refers():
    result = rules.evaluate(_submission(roof_age_years=25))
    assert result.preliminary_decision == "REFER"
    assert any(f.code == "RC-202" for f in result.reason_codes)


def test_very_old_roof_declines():
    result = rules.evaluate(_submission(roof_age_years=35))
    assert result.preliminary_decision == "DECLINE"
    assert any(f.code == "RC-201" for f in result.reason_codes)


def test_vacant_declines():
    result = rules.evaluate(_submission(occupancy=OccupancyType.VACANT))
    assert result.preliminary_decision == "DECLINE"
    assert any(f.code == "RC-101" for f in result.reason_codes)


def test_rental_refers():
    result = rules.evaluate(_submission(occupancy=OccupancyType.RENTAL))
    assert result.preliminary_decision == "REFER"
    assert any(f.code == "RC-102" for f in result.reason_codes)


def test_wildfire_without_mitigation_refers():
    result = rules.evaluate(
        _submission(wildfire_mitigation=False),
        {"hazard_profile": {"wildfire_band": "very_high"}},
    )
    assert any(f.code == "RC-601" for f in result.reason_codes)


def test_knockout_beats_referral():
    # Vacant (knockout) plus old roof (referral) -> DECLINE wins.
    result = rules.evaluate(
        _submission(occupancy=OccupancyType.VACANT, roof_age_years=25)
    )
    assert result.preliminary_decision == "DECLINE"
