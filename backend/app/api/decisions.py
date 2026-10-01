"""Human final decision. Only a chair or administrator may record it, and it is mandatory
before a case can be resolved. The decision references the AI findings accepted or rejected."""
import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import audit
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..domain import DECISION_STATUSES
from ..integrity import sha256_text, canonical_json
from ..ledger import append_integrity, now_iso
from ..refs import next_ref

router = APIRouter(prefix="/api/cases/{case_id}", tags=["decision"])

DECISION_ROLES = {"CHAIR", "ADMIN"}

# human decision -> case status
STATUS_MAP = {
    "RESOLVED_BY_AGREEMENT": ("RESOLVED", "CLOSED"),
    "PRELIMINARY_RESOLUTION_ACCEPTED": ("RESOLVED", "CLOSED"),
    "ADDITIONAL_EVIDENCE_REQUIRED": ("EVIDENCE_REQUESTED", "EVIDENCE_REQUESTS"),
    "REFERRED_FOR_FURTHER_PROCEEDINGS": ("AWAITING_REVIEW", "HUMAN_REVIEW"),
    "ESCALATED_TO_AUTHORITY": ("ESCALATED", "CLOSED"),
    "CLOSED_WITHOUT_RESOLUTION": ("CLOSED", "CLOSED"),
}


class DecisionIn(BaseModel):
    status: str
    decision: str
    reason: str
    evidence_ids: list[str] = []
    legal_refs: list[str] = []
    observations: str = ""


@router.get("/decision")
def get_decision(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        row = c.execute("SELECT * FROM decisions WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        for k in ("evidence_ids", "legal_refs", "accepted_finding_ids", "rejected_finding_ids"):
            try:
                d[k] = json.loads(d[k] or "[]")
            except json.JSONDecodeError:
                d[k] = []
        return d


@router.post("/decision", status_code=201)
def record_decision(case_id: str, body: DecisionIn, user: dict = Depends(get_current_user)):
    if user["role"] not in DECISION_ROLES:
        raise HTTPException(403, f"ROLE {user['role']} MAY NOT RECORD A DECISION")
    if body.status not in DECISION_STATUSES:
        raise HTTPException(422, f"INVALID DECISION STATUS: {body.status}")
    if not body.decision.strip() or not body.reason.strip():
        raise HTTPException(422, "A DECISION AND A REASON ARE REQUIRED")
    with db() as c:
        assert_case_access(c, case_id, user)
        if c.execute("SELECT 1 FROM decisions WHERE case_id=?", (case_id,)).fetchone():
            raise HTTPException(409, "A DECISION HAS ALREADY BEEN RECORDED FOR THIS CASE")
        accepted = [r["finding_ref"] for r in c.execute(
            "SELECT finding_ref FROM ai_findings WHERE case_id=? AND human_status IN ('ACCEPT','EDIT')", (case_id,))]
        rejected = [r["finding_ref"] for r in c.execute(
            "SELECT finding_ref FROM ai_findings WHERE case_id=? AND human_status IN ('REJECT','MARK_UNRESOLVED')", (case_id,))]
        ref = next_ref(c, case_id, "decision", "D")
        payload = {"decision_ref": ref, "status": body.status, "decision": body.decision, "reason": body.reason,
                   "evidence_ids": body.evidence_ids, "legal_refs": body.legal_refs, "observations": body.observations,
                   "accepted": accepted, "rejected": rejected, "decided_by": user["id"], "decided_at": now_iso()}
        cur = c.execute(
            "INSERT INTO decisions(case_id, decision_ref, status, decision, reason, evidence_ids, legal_refs,"
            " accepted_finding_ids, rejected_finding_ids, observations, decided_by, decided_at, human_validated)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (case_id, ref, body.status, body.decision, body.reason, json.dumps(body.evidence_ids), json.dumps(body.legal_refs),
             json.dumps(accepted), json.dumps(rejected), body.observations, user["id"], now_iso()))
        did = cur.lastrowid
        object_hash = sha256_text(canonical_json(payload))
        append_integrity(c, case_id=case_id, kind="DECISION", object_type="decision", object_id=ref, object_hash=object_hash)
        status, stage = STATUS_MAP[body.status]
        c.execute("UPDATE cases SET status=?, current_stage=?, next_action=?, updated_at=? WHERE id=?",
                  (status, stage, "Case closed" if status in ("RESOLVED", "CLOSED", "ESCALATED") else "Continue case work",
                   now_iso(), case_id))
        audit.record(c, user, "DECISION_RECORDED", case_id=case_id, object_type="decision", object_id=ref,
                     new_state=body.status, detail=body.decision[:200])
        return dict(c.execute("SELECT * FROM decisions WHERE id=?", (did,)).fetchone())
