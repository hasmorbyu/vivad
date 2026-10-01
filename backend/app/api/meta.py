"""Reference data for the UI, served from the backend so labels never drift from the API."""
from fastapi import APIRouter

from ..domain import (CASE_CATEGORIES, CASE_STATUSES, CATEGORY_LABELS, CLAIM_STATUSES, CONTRADICTION_KINDS,
                      DECISION_LABELS, DECISION_STATUSES, ESCALATION_CATEGORIES, FINDING_KINDS, PARTY_ROLES,
                      PRIORITY, STAGES, URGENCY)

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("")
def meta():
    return {
        "categories": [{"value": c, "label": CATEGORY_LABELS[c], "escalation": c in ESCALATION_CATEGORIES} for c in CASE_CATEGORIES],
        "case_statuses": CASE_STATUSES,
        "stages": STAGES,
        "urgency": URGENCY,
        "priority": PRIORITY,
        "party_roles": PARTY_ROLES,
        "claim_statuses": CLAIM_STATUSES,
        "contradiction_kinds": CONTRADICTION_KINDS,
        "finding_kinds": FINDING_KINDS,
        "decision_statuses": [{"value": d, "label": DECISION_LABELS[d]} for d in DECISION_STATUSES],
    }
