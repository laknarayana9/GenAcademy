"""Human-friendly labels, colors, and option maps for the UI.

Keeps internal enum/code values out of the user-facing copy and centralizes the
mapping between API node names and the agent pipeline shown to applicants.
"""

from __future__ import annotations

# --- Form option maps (label -> API value) -------------------------------
CONSTRUCTION_OPTIONS = {
    "Wood frame": "frame",
    "Masonry (brick/block)": "masonry",
    "Masonry veneer": "masonry_veneer",
    "Fire-resistive (concrete/steel)": "fire_resistive",
    "Manufactured / mobile": "manufactured",
}

ROOF_OPTIONS = {
    "Asphalt shingle": "asphalt_shingle",
    "Metal": "metal",
    "Tile": "tile",
    "Wood shake": "wood_shake",
    "Flat / built-up": "flat_built_up",
}

OCCUPANCY_OPTIONS = {
    "Owner — primary residence": "owner_primary",
    "Owner — secondary home": "owner_secondary",
    "Seasonal": "seasonal",
    "Rental": "rental",
    "Vacant": "vacant",
}

US_STATES = [
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY",
]

# --- Decision + status styling -------------------------------------------
RECOMMENDATION_STYLE = {
    "ACCEPT": {"color": "#16a34a", "emoji": "✅", "headline": "Quote Approved"},
    "REFER": {"color": "#d97706", "emoji": "🔎", "headline": "Referred to Underwriting"},
    "DECLINE": {"color": "#dc2626", "emoji": "⛔", "headline": "Quote Declined"},
}

STATUS_STYLE = {
    "processing": {"color": "#2563eb", "label": "Processing"},
    "waiting_for_info": {"color": "#d97706", "label": "Needs Information"},
    "pending_review": {"color": "#7c3aed", "label": "Pending Review"},
    "completed": {"color": "#16a34a", "label": "Completed"},
    "failed": {"color": "#dc2626", "label": "Failed"},
}

PRIORITY_STYLE = {
    "high": {"color": "#dc2626", "label": "High"},
    "medium": {"color": "#d97706", "label": "Medium"},
    "low": {"color": "#16a34a", "label": "Low"},
}

SEVERITY_STYLE = {
    "knockout": "#dc2626",
    "referral": "#d97706",
    "info": "#2563eb",
    "pass": "#16a34a",
}

TRIGGER_LABEL = {
    "missing_info": "Missing information",
    "refer": "Referral",
    "decline": "Decline confirmation",
    "verification_failure": "Verification failure",
}

# --- Agent pipeline (node -> friendly step) ------------------------------
PIPELINE_STEPS = [
    ("normalize", "Intake & validation"),
    ("route", "Routing"),
    ("enrich", "Hazard & territory enrichment"),
    ("retrieve", "Guideline retrieval"),
    ("assess", "Underwriting assessment"),
    ("verify", "Grounding & verification"),
    ("critic", "Critique"),
    ("package", "Decision packaging"),
    ("route_decision", "Final routing"),
    ("create_review_task", "Review task created"),
]

NODE_LABEL = dict(PIPELINE_STEPS)


def occupancy_label(value: str) -> str:
    for label, val in OCCUPANCY_OPTIONS.items():
        if val == value:
            return label
    return value
