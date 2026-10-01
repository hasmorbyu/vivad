"""Structured statements captured from each party in plain language."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import audit
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..ledger import now_iso
from ..refs import touch

router = APIRouter(prefix="/api/cases/{case_id}/statements", tags=["statements"])


class StatementIn(BaseModel):
    party_id: int | None = None
    kind: str = "INITIAL"
    what: str = ""
    when_text: str = ""
    where_text: str = ""
    who: str = ""
    claim: str = ""
    evidence_support: str = ""
    desired_resolution: str = ""


@router.get("")
def list_statements(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        rows = []
        for r in c.execute("SELECT s.*, p.name party_name, p.role party_role FROM statements s LEFT JOIN parties p ON p.id=s.party_id WHERE s.case_id=? ORDER BY s.id", (case_id,)):
            rows.append(dict(r))
        return rows


@router.post("", status_code=201)
def add_statement(case_id: str, body: StatementIn, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        if body.party_id is not None:
            if not c.execute("SELECT 1 FROM parties WHERE id=? AND case_id=?", (body.party_id, case_id)).fetchone():
                raise HTTPException(422, "PARTY DOES NOT BELONG TO THIS CASE")
        cur = c.execute(
            "INSERT INTO statements(case_id, party_id, kind, what, when_text, where_text, who, claim, evidence_support,"
            " desired_resolution, submitted_by, submitted_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, body.party_id, body.kind, body.what, body.when_text, body.where_text, body.who, body.claim,
             body.evidence_support, body.desired_resolution, user["id"], now_iso()))
        sid = cur.lastrowid
        c.execute("UPDATE cases SET current_stage='STATEMENTS', updated_at=? WHERE id=?", (now_iso(), case_id))
        touch(c, case_id)
        audit.record(c, user, "STATEMENT_SUBMITTED", case_id=case_id, object_type="statement", object_id=sid,
                     new_state=body.kind, detail=(body.claim or body.what)[:200])
        return dict(c.execute("SELECT * FROM statements WHERE id=?", (sid,)).fetchone())
