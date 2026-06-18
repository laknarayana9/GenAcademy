# HO3 General Eligibility Guidelines (Synthetic)

> SYNTHETIC DATA. These guidelines are fictional and for demonstration only.
> They do not represent any real carrier's underwriting manual.

## Section 1.1 — Product Scope

The HO3 special form provides open-peril coverage on the dwelling and
named-peril coverage on personal property. Eligibility requires an owner-occupied
or owner-secondary one-to-four family dwelling. All evaluated submissions begin
from a baseline of acceptance and are adjusted by the referral and knockout rules
below. When no referral or knockout rule applies, the submission is eligible for
straight-through acceptance (reason code RC-001).

## Section 1.2 — Dwelling Age (RC-301)

Dwellings built before 1950 must be referred for verification that electrical,
plumbing, heating, and roofing systems have been updated to current code. This is
referral reason code RC-301. Dwellings built in 1950 or later do not trigger this
rule on age alone.

## Section 1.3 — Coverage Amount Bands

The insurable dwelling amount (Coverage A) must fall within the standard band.

- High-value referral (RC-401): A dwelling amount above $2,000,000 exceeds the
  standard high-value threshold and must be referred to the high-value unit.
- Minimum insurable referral (RC-402): A dwelling amount below $75,000 indicates a
  possible rebuild-cost mismatch and must be referred for valuation review.

Submissions inside the band ($75,000 to $2,000,000 inclusive) are eligible on the
coverage-amount dimension.

## Section 1.4 — Liability Limits (RC-801)

Personal liability limits above $1,000,000 are above the standard offering and
must be referred for excess liability review (RC-801). Standard liability limits
up to and including $1,000,000 are acceptable.

## Section 1.5 — Decision Aggregation

When multiple rules trigger, the strongest severity governs the overall
recommendation: any knockout produces DECLINE, otherwise any referral produces
REFER, otherwise the submission is ACCEPT. Deterministic rules are the source of
truth and are never overridden by narrative rationale.
