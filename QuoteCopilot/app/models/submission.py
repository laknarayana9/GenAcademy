"""Submission models: legacy intake payload and canonical HO3 submission.

`LegacyQuotePayload` is the loose, producer-facing shape accepted at
`POST /quote/run`. `HO3CanonicalSubmission` is the validated internal shape the
graph operates on, accepted directly at `POST /quote/ho3`. The Normalizer agent
maps the former into the latter.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ConstructionType(str, Enum):
    """Primary construction class affecting eligibility and rating."""

    FRAME = "frame"
    MASONRY = "masonry"
    MASONRY_VENEER = "masonry_veneer"
    FIRE_RESISTIVE = "fire_resistive"
    MANUFACTURED = "manufactured"


class OccupancyType(str, Enum):
    """How the dwelling is occupied; drives knockout eligibility."""

    OWNER_PRIMARY = "owner_primary"
    OWNER_SECONDARY = "owner_secondary"
    SEASONAL = "seasonal"
    RENTAL = "rental"
    VACANT = "vacant"


class RoofType(str, Enum):
    """Roof covering material."""

    ASPHALT_SHINGLE = "asphalt_shingle"
    METAL = "metal"
    TILE = "tile"
    WOOD_SHAKE = "wood_shake"
    FLAT_BUILT_UP = "flat_built_up"


class CoverageRequest(BaseModel):
    """Requested coverage and deductible inputs for rating."""

    model_config = ConfigDict(extra="forbid")

    dwelling_amount: float = Field(..., gt=0, description="Coverage A dwelling limit, USD")
    deductible: float = Field(..., ge=0, description="All-peril deductible, USD")
    liability_limit: float | None = Field(
        default=None, ge=0, description="Personal liability limit, USD"
    )


class ClaimRecord(BaseModel):
    """A single prior loss on the property or applicant."""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., ge=1900, le=2100)
    peril: str
    amount: float = Field(..., ge=0)


class HO3CanonicalSubmission(BaseModel):
    """Validated canonical HO3 submission consumed by the graph."""

    model_config = ConfigDict(extra="forbid")

    quote_id: str
    applicant_name: str

    # --- Location ---
    state: str = Field(..., min_length=2, max_length=2, description="USPS state code")
    zip_code: str = Field(..., pattern=r"^\d{5}$")

    # --- Dwelling characteristics ---
    year_built: int = Field(..., ge=1800, le=2100)
    construction_type: ConstructionType
    roof_type: RoofType
    roof_age_years: int | None = Field(
        default=None, ge=0, le=150, description="None means the fact is missing"
    )
    square_feet: int = Field(..., gt=0)
    stories: int = Field(default=1, ge=1, le=4)

    # --- Use / occupancy ---
    occupancy: OccupancyType

    # --- Coverage + history ---
    coverage: CoverageRequest
    prior_claims: list[ClaimRecord] = Field(default_factory=list)

    # --- Hazard hints (optional; enrichment may supersede) ---
    wildfire_mitigation: bool | None = Field(
        default=None,
        description="Defensible space / hardened construction present; None if unknown",
    )
    distance_to_coast_miles: float | None = Field(default=None, ge=0)


class LegacyQuotePayload(BaseModel):
    """Loose legacy producer payload; normalized into the canonical shape.

    Fields are permissive on purpose so intake can detect and surface missing
    facts rather than rejecting the whole submission.
    """

    model_config = ConfigDict(extra="allow")

    quote_id: str | None = None
    name: str | None = None
    address_state: str | None = None
    zip: str | None = None
    year_built: int | None = None
    construction: str | None = None
    roof: str | None = None
    roof_age: int | None = None
    sq_ft: int | None = None
    use: str | None = None
    coverage_a: float | None = None
    deductible: float | None = None
    liability: float | None = None
    claims: list[dict] | None = None
    notes: str | None = None
