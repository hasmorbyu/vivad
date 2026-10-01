"""Parties to a dispute: the people and organisations involved, with their role."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import audit
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..domain import PARTY_ROLES
from ..ledger import now_iso
from ..refs import touch

router = APIRouter(prefix="/api/cases/{case_id}/parties", tags=["parties"])


class PartyIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    role: str = "COMPLAINANT"
    contact: str = ""
    relationship: str = ""
    user_id: int | None = None


@router.get("")
def list_parties(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        return [dict(r) for r in c.execute("SELECT * FROM parties WHERE case_id=? ORDER BY id", (case_id,))]


@router.post("", status_code=201)
def add_party(case_id: str, body: PartyIn, user: dict = Depends(get_current_user)):
    if body.role not in PARTY_ROLES:
        raise HTTPException(422, f"INVALID PARTY ROLE: {body.role}")
    with db() as c:
        assert_case_access(c, case_id, user)
        cur = c.execute("INSERT INTO parties(case_id, name, role, contact, relationship, user_id, created_at) VALUES(?,?,?,?,?,?,?)",
                        (case_id, body.name.strip(), body.role, body.contact, body.relationship, body.user_id, now_iso()))
        party_id = cur.lastrowid
        # advance intake stage once both sides are present
        roles = {r[0] for r in c.execute("SELECT DISTINCT role FROM parties WHERE case_id=?", (case_id,))}
        if "COMPLAINANT" in roles and "RESPONDENT" in roles:
            c.execute("UPDATE cases SET current_stage='EVIDENCE', status='PROCESSING', next_action='Upload and process evidence', updated_at=? WHERE id=?",
                      (now_iso(), case_id))
        else:
            c.execute("UPDATE cases SET current_stage='PARTIES', updated_at=? WHERE id=?", (now_iso(), case_id))
        touch(c, case_id)
        audit.record(c, user, "PARTY_ADDED", case_id=case_id, object_type="party", object_id=party_id,
                     new_state=body.role, detail=body.name.strip())
        return dict(c.execute("SELECT * FROM parties WHERE id=?", (party_id,)).fetchone())


@router.patch("/{party_id}")
def patch_party(case_id: str, party_id: int, body: PartyIn, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        row = c.execute("SELECT * FROM parties WHERE id=? AND case_id=?", (party_id, case_id)).fetchone()
        if not row:
            raise HTTPException(404, "PARTY NOT FOUND")
        if body.role not in PARTY_ROLES:
            raise HTTPException(422, f"INVALID PARTY ROLE: {body.role}")
        c.execute("UPDATE parties SET name=?, role=?, contact=?, relationship=?, user_id=? WHERE id=?",
                  (body.name.strip(), body.role, body.contact, body.relationship, body.user_id, party_id))
        touch(c, case_id)
        audit.record(c, user, "PARTY_UPDATED", case_id=case_id, object_type="party", object_id=party_id,
                     prev_state=row["role"], new_state=body.role, detail=body.name.strip())
        return dict(c.execute("SELECT * FROM parties WHERE id=?", (party_id,)).fetchone())


@router.delete("/{party_id}")
def delete_party(case_id: str, party_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        row = c.execute("SELECT * FROM parties WHERE id=? AND case_id=?", (party_id, case_id)).fetchone()
        if not row:
            raise HTTPException(404, "PARTY NOT FOUND")
        c.execute("DELETE FROM parties WHERE id=?", (party_id,))
        audit.record(c, user, "PARTY_REMOVED", case_id=case_id, object_type="party", object_id=party_id,
                     prev_state=row["role"], detail=row["name"])
        return {"ok": True}
