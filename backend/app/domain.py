"""Shared domain constants. Wording here is deliberately non-adjudicatory.

VIVAD is a preliminary dispute-resolution aid. Nothing in this module labels any party as
guilty, dishonest or liable; classifications describe the strength of a documentary link.
"""

CASE_CATEGORIES = [
    "PAYMENT_DISPUTE",
    "RENTAL_DISPUTE",
    "CONSUMER_SERVICE_DISPUTE",
    "CONTRACT_DISPUTE",
    "PROPERTY_POSSESSION_DISPUTE",
    "DAMAGE_COMPENSATION_DISPUTE",
    "NEIGHBOURHOOD_DISPUTE",
    "INSTITUTIONAL_DISPUTE",
    "OTHER",
]

CATEGORY_LABELS = {
    "PAYMENT_DISPUTE": "Payment dispute",
    "RENTAL_DISPUTE": "Rental dispute",
    "CONSUMER_SERVICE_DISPUTE": "Consumer / service dispute",
    "CONTRACT_DISPUTE": "Contract dispute",
    "PROPERTY_POSSESSION_DISPUTE": "Property / possession dispute",
    "DAMAGE_COMPENSATION_DISPUTE": "Damage / compensation dispute",
    "NEIGHBOURHOOD_DISPUTE": "Neighbourhood dispute",
    "INSTITUTIONAL_DISPUTE": "Institutional dispute",
    "OTHER": "Other",
}

# Categories outside VIVAD's intended remit must be routed to an authority, not analysed here.
ESCALATION_CATEGORIES = {"PROPERTY_POSSESSION_DISPUTE"}

URGENCY = ["LOW", "NORMAL", "HIGH", "URGENT"]
PRIORITY = ["LOW", "NORMAL", "HIGH"]

# Case lifecycle. "current_stage" tracks the user journey shown in the UI.
STAGES = [
    "INTAKE",
    "PARTIES",
    "STATEMENTS",
    "EVIDENCE",
    "PROCESSING",
    "ANALYSIS",
    "HUMAN_REVIEW",
    "EVIDENCE_REQUESTS",
    "HEARING",
    "DECISION",
    "CLOSED",
]

CASE_STATUSES = [
    "INTAKE",
    "AWAITING_RESPONSE",
    "PROCESSING",
    "AWAITING_REVIEW",
    "AWAITING_COMMITTEE_REVIEW",
    "EVIDENCE_REQUESTED",
    "HEARING_SCHEDULED",
    "AWAITING_DECISION",
    "RESOLVED",
    "ESCALATED",
    "CLOSED",
]

# How each party-related role is shown. Never "complainant = victim" or "respondent = accused".
PARTY_ROLES = ["COMPLAINANT", "RESPONDENT", "WITNESS", "OTHER"]

# Epistemic labels shared with the frontend. Order is fixed: strongest first.
CLASSIFICATIONS = {
    "DIRECT_IDENTIFIER_MATCH": ("[✓]", "VERIFIED", "DIRECT IDENTIFIER MATCH"),
    "EXPLICIT_ASSOCIATION": ("[■]", "DIRECT", "EXPLICIT ASSOCIATION"),
    "CONTEXTUAL_LEAD": ("[□]", "LEAD", "CONTEXTUAL LEAD"),
    "UNRESOLVED": ("[?]", "UNRESOLVED", "UNRESOLVED"),
}

CLAIM_STATUSES = [
    "SUPPORTED",
    "PARTIALLY_SUPPORTED",
    "CONTRADICTED",
    "UNSUPPORTED",
    "UNRESOLVED",
    "REQUIRES_HUMAN_REVIEW",
]

CONTRADICTION_KINDS = {
    "TEMPORAL": "Temporal contradiction",
    "AMOUNT": "Amount mismatch",
    "IDENTITY": "Identity mismatch",
    "STATEMENT_EVIDENCE": "Statement-evidence conflict",
    "CROSS_PARTY": "Cross-party contradiction",
    "MISSING_SUPPORT": "Missing supporting evidence",
}

FINDING_KINDS = [
    "FACT_SUPPORTED",
    "CLAIM_REQUIRING_VERIFICATION",
    "CONTRADICTION",
    "MISSING_INFORMATION",
    "RELEVANT_EVIDENCE",
    "LEGAL_REFERENCE",
    "RESOLUTION_PATH",
    "HEARING_QUESTION",
]

DECISION_STATUSES = [
    "RESOLVED_BY_AGREEMENT",
    "PRELIMINARY_RESOLUTION_ACCEPTED",
    "ADDITIONAL_EVIDENCE_REQUIRED",
    "REFERRED_FOR_FURTHER_PROCEEDINGS",
    "ESCALATED_TO_AUTHORITY",
    "CLOSED_WITHOUT_RESOLUTION",
]

DECISION_LABELS = {
    "RESOLVED_BY_AGREEMENT": "Resolved by agreement",
    "PRELIMINARY_RESOLUTION_ACCEPTED": "Preliminary resolution accepted",
    "ADDITIONAL_EVIDENCE_REQUIRED": "Additional evidence required",
    "REFERRED_FOR_FURTHER_PROCEEDINGS": "Referred for further proceedings",
    "ESCALATED_TO_AUTHORITY": "Escalated to appropriate authority",
    "CLOSED_WITHOUT_RESOLUTION": "Closed without resolution",
}

# Trust labels used throughout the UI to separate machine output from human validation.
TRUST_LABELS = {
    "AI": "AI-ASSISTED ANALYSIS",
    "HUMAN": "HUMAN-VALIDATED",
    "EVIDENCE": "EVIDENCE-DERIVED",
    "VERIFY": "REQUIRES VERIFICATION",
}
