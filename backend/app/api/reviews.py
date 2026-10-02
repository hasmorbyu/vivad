"""Human review of AI findings, and evidence requests.

No AI output becomes a decision without a human action. Every review is recorded with the
reviewer, timestamp and comment, and produces an audit event.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import audit
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..ledger import now_iso
from ..notify import notify_case_parties
from ..services import parse_json

router = APIRouter(prefix="/api/cases/{case_id}", tags=["review"])

REVIEW_ROLES = {"CASE_OFFICER", "REVIEWER", "CHAIR", "ADMIN"}
ACTIONS = {"ACCEPT", "REJECT", "EDIT", "REQUEST_EVIDENCE", "MARK_UNRESOLVED"}
ACTION_EVENT = {"ACCEPT": "FINDING_ACCEPTED", "REJECT": "FINDING_REJECTED", "EDIT": "FINDING_EDITED",
                "REQUEST_EVIDENCE": "EVIDENCE_REQUESTED", "MARK_UNRESOLVED": "FINDING_MARKED_UNRESOLVED"}


class ReviewIn(BaseModel):
    finding_id: int
    action: str
    edited_body: str = ""
    comment: str = ""


class EvidenceRequestIn(BaseModel):
    about: str
    note: str = ""
    party_id: int | None = None


def _require_reviewer(user):
    if user["role"] not in REVIEW_ROLES:
        raise HTTPException(403, f"ROLE {user['role']} MAY NOT REVIEW FINDINGS")


@router.get("/reviews")
def list_reviews(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        findings = []
        for f in c.execute("SELECT * FROM ai_findings WHERE case_id=? ORDER BY finding_ref", (case_id,)):
            d = dict(f)
            refs = parse_json(d["evidence_ids"], [])
            d["evidence_ids"] = refs
            d["evidence"] = [dict(e) for e in c.execute(
                f"SELECT id, evidence_ref FROM evidence WHERE case_id=? AND evidence_ref IN ({','.join('?' * len(refs))})",
                (case_id, *refs))] if refs else []
            findings.append(d)
        history = [dict(r) for r in c.execute(
            "SELECT hr.*, u.display_name reviewer_name, u.role reviewer_role FROM human_reviews hr "
            "LEFT JOIN users u ON u.id=hr.reviewer_id WHERE hr.case_id=? ORDER BY hr.id DESC", (case_id,))]
        return {"findings": findings, "history": history}


@router.post("/reviews", status_code=201)
def review_finding(case_id: str, body: ReviewIn, user: dict = Depends(get_current_user)):
    _require_reviewer(user)
    if body.action not in ACTIONS:
        raise HTTPException(422, f"INVALID ACTION: {body.action}")
    with db() as c:
        assert_case_access(c, case_id, user)
        f = c.execute("SELECT * FROM ai_findings WHERE id=? AND case_id=?", (body.finding_id, case_id)).fetchone()
        if not f:
            raise HTTPException(404, "FINDING NOT FOUND")
        new_body = body.edited_body if body.action == "EDIT" and body.edited_body else f["body"]
        c.execute("UPDATE ai_findings SET human_status=?, reviewer_id=?, reviewed_at=?, body=? WHERE id=?",
                  (body.action, user["id"], now_iso(), new_body, f["id"]))
        cur = c.execute(
            "INSERT INTO human_reviews(case_id, finding_id, action, edited_body, comment, reviewer_id, created_at) VALUES(?,?,?,?,?,?,?)",
            (case_id, f["id"], body.action, body.edited_body or None, body.comment, user["id"], now_iso()))
        audit.record(c, user, ACTION_EVENT[body.action], case_id=case_id, object_type="ai_finding",
                     object_id=f["finding_ref"], prev_state=f["human_status"], new_state=body.action,
                     detail=body.comment[:200])
        return dict(c.execute("SELECT * FROM ai_findings WHERE id=?", (f["id"],)).fetchone()) | {"review_id": cur.lastrowid}


@router.get("/evidence-requests")
def list_evidence_requests(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        return [dict(r) for r in c.execute(
            "SELECT er.*, p.name party_name FROM evidence_requests er LEFT JOIN parties p ON p.id=er.party_id "
            "WHERE er.case_id=? ORDER BY er.id DESC", (case_id,))]


@router.post("/evidence-requests", status_code=201)
def request_evidence(case_id: str, body: EvidenceRequestIn, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        if not body.about.strip():
            raise HTTPException(422, "A REQUEST MUST STATE WHAT IS NEEDED")
        cur = c.execute(
            "INSERT INTO evidence_requests(case_id, about, note, party_id, requested_by, status, created_at) VALUES(?,?,?,?,?,?,?)",
            (case_id, body.about.strip(), body.note, body.party_id, user["id"], "OPEN", now_iso()))
        if not c.execute("SELECT 1 FROM decisions WHERE case_id=?", (case_id,)).fetchone():
            c.execute("UPDATE cases SET status='EVIDENCE_REQUESTED', current_stage='EVIDENCE_REQUESTS', next_action=? WHERE id=?",
                      (f"Awaiting response: {body.about[:60]}", case_id))
        target = [body.party_id] if body.party_id else None
        if target:
            p = c.execute("SELECT user_id FROM parties WHERE id=?", (body.party_id,)).fetchone()
            if p and p["user_id"]:
                from ..notify import notify
                notify(c, case_id=case_id, user_id=p["user_id"], kind="EVIDENCE_REQUEST",
                       title="Additional evidence requested", body=body.about)
        else:
            notify_case_parties(c, case_id, "EVIDENCE_REQUEST", "Additional evidence requested", body.about)
        audit.record(c, user, "EVIDENCE_REQUESTED", case_id=case_id, object_type="evidence_request",
                     object_id=cur.lastrowid, new_state="OPEN", detail=body.about[:200])
        return dict(c.execute("SELECT * FROM evidence_requests WHERE id=?", (cur.lastrowid,)).fetchone())
