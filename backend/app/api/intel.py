"""Analysis control and the intelligence read models: claims, contradictions, timeline, legal, findings."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import analysis, audit
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..domain import CONTRADICTION_KINDS
from ..ledger import now_iso
from ..services import parse_json

router = APIRouter(prefix="/api/cases/{case_id}", tags=["intelligence"])


@router.post("/analyze", status_code=202)
def run_analysis(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
    if not analysis.start_analysis(case_id, user):
        raise HTTPException(409, "ANALYSIS ALREADY RUNNING")
    return analysis.get_status(case_id)


@router.get("/analyze/status")
def analyze_status(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
    return analysis.get_status(case_id)


@router.get("/analysis")
def get_analysis(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        run = c.execute("SELECT * FROM ai_analyses WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
        findings = []
        for f in c.execute("SELECT * FROM ai_findings WHERE case_id=? ORDER BY finding_ref", (case_id,)):
            d = dict(f)
            d["evidence_ids"] = parse_json(d["evidence_ids"], [])
            d["claim_ids"] = parse_json(d["claim_ids"], [])
            findings.append(d)
        grouped: dict[str, list] = {}
        for f in findings:
            grouped.setdefault(f["kind"], []).append(f)
        return {"run": ({**dict(run), "input_json": parse_json(run["input_json"], {}),
                         "output_json": parse_json(run["output_json"], {})} if run else None),
                "analysis": parse_json(run["output_json"], {}) if run else {},
                "validation": run["validation"] if run else None,
                "provider": run["provider"] if run else None,
                "status": run["status"] if run else None,
                "findings": findings, "grouped": grouped,
                "awaiting_review": sum(1 for f in findings if f["human_status"] == "PENDING")}


@router.get("/claims")
def list_claims(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        out = []
        for r in c.execute("SELECT cl.*, p.name party_name, p.role party_role FROM claims cl LEFT JOIN parties p ON p.id=cl.party_id WHERE cl.case_id=? ORDER BY cl.id", (case_id,)):
            d = dict(r)
            d["evidence"] = [{"id": x["id"], "evidence_ref": x["evidence_ref"], "filename": x["filename"], "relationship": x["relationship"]}
                             for x in c.execute("SELECT ev.id, ev.evidence_ref, ev.filename, er.relationship FROM evidence_references er JOIN evidence ev ON ev.id=er.evidence_id WHERE er.claim_id=?", (r["id"],))]
            out.append(d)
        return out


@router.get("/contradictions")
def list_contradictions(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        out = []
        for r in c.execute("SELECT * FROM contradictions WHERE case_id=? ORDER BY contradiction_ref", (case_id,)):
            d = dict(r)
            d["kind_label"] = CONTRADICTION_KINDS.get(d["kind"], d["kind"])
            d["evidence_ids"] = parse_json(d["evidence_ids"], [])
            d["evidence"] = [{"id": eid, "evidence_ref": (e["evidence_ref"] if (e := c.execute("SELECT evidence_ref FROM evidence WHERE id=?", (eid,)).fetchone()) else None)} for eid in d["evidence_ids"]]
            for side in ("a", "b"):
                cid = d[f"claim_{side}_id"]
                claim = c.execute("SELECT cl.claim_ref, cl.text, cl.status, p.name party_name FROM claims cl LEFT JOIN parties p ON p.id=cl.party_id WHERE cl.id=?", (cid,)).fetchone() if cid else None
                d[f"claim_{side}"] = dict(claim) if claim else None
            out.append(d)
        return out


class ContradictionPatch(BaseModel):
    verification_status: str
    note: str = ""


@router.patch("/contradictions/{contradiction_ref}")
def review_contradiction(case_id: str, contradiction_ref: str, body: ContradictionPatch, user: dict = Depends(get_current_user)):
    allowed = {"REQUIRES_HUMAN_REVIEW", "CONFIRMED_INCONSISTENCY", "DISMISSED", "ESCALATED"}
    if body.verification_status not in allowed:
        raise HTTPException(422, f"INVALID STATUS: {body.verification_status}")
    with db() as c:
        assert_case_access(c, case_id, user)
        row = c.execute("SELECT * FROM contradictions WHERE case_id=? AND contradiction_ref=?", (case_id, contradiction_ref)).fetchone()
        if not row:
            raise HTTPException(404, "CONTRADICTION NOT FOUND")
        c.execute("UPDATE contradictions SET verification_status=?, reviewed_by=?, reviewed_at=? WHERE id=?",
                  (body.verification_status, user["id"], now_iso(), row["id"]))
        audit.record(c, user, "CONTRADICTION_REVIEWED", case_id=case_id, object_type="contradiction",
                     object_id=contradiction_ref, prev_state=row["verification_status"], new_state=body.verification_status,
                     detail=body.note[:200])
        return dict(c.execute("SELECT * FROM contradictions WHERE id=?", (row["id"],)).fetchone())


@router.get("/timeline")
def get_timeline(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        out = []
        for r in c.execute(
            "SELECT e.*, ev.evidence_ref, ev.filename FROM events e LEFT JOIN evidence ev ON ev.id=e.evidence_id "
            "WHERE e.case_id=? ORDER BY e.event_time, e.event_ref", (case_id,)):
            out.append(dict(r))
        return out


@router.get("/legal")
def get_legal(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        out = []
        for r in c.execute(
            "SELECT clr.id, clr.relevance, clr.concepts, clr.status, clr.origin, lr.id legal_reference_id, lr.act, lr.section,"
            " lr.title, lr.description, lr.source_url, lr.last_verified, lr.jurisdiction, lr.disclaimer "
            "FROM case_legal_refs clr JOIN legal_references lr ON lr.id=clr.legal_reference_id WHERE clr.case_id=? ORDER BY clr.id", (case_id,)):
            d = dict(r)
            d["concepts"] = parse_json(d["concepts"], [])
            out.append(d)
        return out


@router.get("/audit")
def get_audit(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        return [dict(r) for r in c.execute(
            "SELECT seq, actor_id, actor_role, action, object_type, object_id, prev_state, new_state, detail, created_at, record_hash "
            "FROM audit_events WHERE case_id=? ORDER BY seq", (case_id,))]
