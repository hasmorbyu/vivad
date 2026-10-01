"""Case intake: create, list, read and update cases with role-scoped visibility."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .. import audit
from ..auth import STAFF_ROLES, assert_case_access, get_current_user
from ..db import db
from ..domain import CASE_CATEGORIES, CASE_STATUSES, URGENCY, PRIORITY
from ..ledger import now_iso
from ..services import case_brief, case_row, next_action_text

router = APIRouter(prefix="/api/cases", tags=["cases"])


class CaseIn(BaseModel):
    category: str = "OTHER"
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    location: str = ""
    incident_date: str = ""
    amount: float = 0
    currency: str = "INR"
    requested_resolution: str = ""
    urgency: str = "NORMAL"
    priority: str = "NORMAL"


class CasePatch(BaseModel):
    status: str | None = None
    priority: str | None = None
    current_stage: str | None = None
    next_action: str | None = None
    title: str | None = None
    description: str | None = None


def _next_case_id(conn) -> str:
    year = datetime.now(timezone.utc).year
    key = f"cases:{year}"
    row = conn.execute("SELECT value FROM counters WHERE name=?", (key,)).fetchone()
    value = (row["value"] if row else 0) + 1
    if row:
        conn.execute("UPDATE counters SET value=? WHERE name=?", (value, key))
    else:
        conn.execute("INSERT INTO counters(name, value) VALUES(?,?)", (key, value))
    return f"VV-{year}-{value:05d}"


@router.get("")
def list_cases(user: dict = Depends(get_current_user)):
    with db() as c:
        if user["role"] in STAFF_ROLES:
            rows = [dict(r) for r in c.execute("SELECT * FROM cases ORDER BY created_at DESC")]
        else:
            rows = [dict(r) for r in c.execute(
                "SELECT DISTINCT c.* FROM cases c LEFT JOIN parties p ON p.case_id=c.id "
                "WHERE c.created_by=? OR p.user_id=? ORDER BY c.created_at DESC", (user["id"], user["id"]))]
        return [case_brief(c, r) for r in rows]


@router.post("", status_code=201)
def create_case(body: CaseIn, user: dict = Depends(get_current_user)):
    if body.category not in CASE_CATEGORIES:
        raise HTTPException(422, f"UNSUPPORTED DISPUTE CATEGORY: {body.category}")
    if body.urgency not in URGENCY or body.priority not in PRIORITY:
        raise HTTPException(422, "INVALID URGENCY OR PRIORITY")
    with db() as c:
        case_id = _next_case_id(c)
        c.execute(
            "INSERT INTO cases(id, category, title, description, location, incident_date, amount, currency,"
            " requested_resolution, urgency, priority, status, current_stage, next_action, created_by, created_at, updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, body.category, body.title.strip(), body.description, body.location, body.incident_date,
             body.amount, body.currency, body.requested_resolution, body.urgency, body.priority,
             "INTAKE", "INTAKE", "Complete intake and add parties", user["id"], now_iso(), now_iso()))
        audit.record(c, user, "CASE_CREATED", case_id=case_id, object_type="case", object_id=case_id,
                     new_state="INTAKE", detail=f"category={body.category}")
        return case_brief(c, case_row(c, case_id))


@router.get("/{case_id}")
def get_case(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        row = case_row(c, case_id)
        if not row:
            raise HTTPException(404, f"CASE NOT FOUND: {case_id}")
        brief = case_brief(c, row)
        brief["next_action"] = row["next_action"] or next_action_text(c, row)
        return brief


@router.patch("/{case_id}")
def patch_case(case_id: str, body: CasePatch, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        row = case_row(c, case_id)
        if not row:
            raise HTTPException(404, f"CASE NOT FOUND: {case_id}")
        updates, args = [], []
        for field in ("status", "priority", "current_stage", "next_action", "title", "description"):
            value = getattr(body, field)
            if value is not None:
                if field == "status" and value not in CASE_STATUSES:
                    raise HTTPException(422, f"INVALID STATUS: {value}")
                updates.append(f"{field}=?")
                args.append(value)
        if not updates:
            return case_brief(c, row)
        updates.append("updated_at=?")
        args.append(now_iso())
        old_status = row["status"]
        args.append(case_id)
        c.execute(f"UPDATE cases SET {', '.join(updates)} WHERE id=?", args)
        new_row = case_row(c, case_id)
        audit.record(c, user, "CASE_UPDATED", case_id=case_id, object_type="case", object_id=case_id,
                     prev_state=old_status, new_state=new_row["status"], detail="; ".join(updates))
        return case_brief(c, new_row)
