"""Hearing scheduling, participation, meeting rooms and structured hearing notes."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .. import audit
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..ledger import now_iso
from ..meetings import room_for
from ..notify import notify_case_parties

case_router = APIRouter(prefix="/api/cases/{case_id}/hearings", tags=["hearings"])
hearing_router = APIRouter(prefix="/api/hearings", tags=["hearings"])

STAFF = {"CASE_OFFICER", "REVIEWER", "CHAIR", "ADMIN"}


class ParticipantIn(BaseModel):
    user_id: int | None = None
    party_id: int | None = None
    name: str = ""
    role: str = "PARTICIPANT"


class HearingIn(BaseModel):
    scheduled_at: str
    duration_min: int = 30
    agenda: str = ""
    participants: list[ParticipantIn] = []


class HearingPatch(BaseModel):
    scheduled_at: str | None = None
    duration_min: int | None = None
    agenda: str | None = None
    status: str | None = None


class NotesIn(BaseModel):
    issue: str = ""
    party_a: str = ""
    party_b: str = ""
    additional_evidence: str = ""
    next_action: str = ""


def _hearing(c, hearing_id, user):
    h = c.execute("SELECT * FROM hearings WHERE id=?", (hearing_id,)).fetchone()
    if not h:
        raise HTTPException(404, "HEARING NOT FOUND")
    assert_case_access(c, h["case_id"], user)
    return h


@case_router.get("")
def list_hearings(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        out = []
        for h in c.execute("SELECT * FROM hearings WHERE case_id=? ORDER BY scheduled_at", (case_id,)):
            d = dict(h)
            d["participants"] = [dict(p) for p in c.execute(
                "SELECT id, name, role, user_id, party_id, invited, attended FROM hearing_participants WHERE hearing_id=?", (h["id"],))]
            out.append(d)
        return out


@case_router.post("", status_code=201)
def schedule_hearing(case_id: str, body: HearingIn, user: dict = Depends(get_current_user)):
    if user["role"] not in STAFF:
        raise HTTPException(403, f"ROLE {user['role']} MAY NOT SCHEDULE HEARINGS")
    if not body.scheduled_at.strip():
        raise HTTPException(422, "A DATE AND TIME ARE REQUIRED")
    with db() as c:
        assert_case_access(c, case_id, user)
        meeting = room_for(case_id, 0)
        cur = c.execute(
            "INSERT INTO hearings(case_id, scheduled_at, duration_min, status, agenda, provider, room_id, created_by, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (case_id, body.scheduled_at, body.duration_min, "SCHEDULED", body.agenda, meeting.provider, meeting.room_id,
             user["id"], now_iso()))
        hid = cur.lastrowid
        # the room id embeds the hearing id, so update it now that we have one
        room = room_for(case_id, hid)
        c.execute("UPDATE hearings SET provider=?, room_id=? WHERE id=?", (room.provider, room.room_id, hid))
        parts = body.participants or _default_participants(c, case_id)
        for p in parts:
            name = p.name
            if not name and p.party_id:
                row = c.execute("SELECT name, role FROM parties WHERE id=?", (p.party_id,)).fetchone()
                name = row["name"] if row else ""
                p.role = p.role if p.role != "PARTICIPANT" else (row["role"] if row else p.role)
            c.execute("INSERT INTO hearing_participants(hearing_id, user_id, party_id, name, role, invited) VALUES(?,?,?,?,?,1)",
                      (hid, p.user_id, p.party_id, name, p.role))
        c.execute("UPDATE cases SET status='HEARING_SCHEDULED', current_stage='HEARING', next_action=? WHERE id=?",
                  (f"Hearing on {body.scheduled_at}", case_id))
        notify_case_parties(c, case_id, "HEARING_SCHEDULED", "Hearing scheduled", f"{body.scheduled_at} · {body.agenda}")
        audit.record(c, user, "HEARING_SCHEDULED", case_id=case_id, object_type="hearing", object_id=hid,
                     new_state="SCHEDULED", detail=f"{body.scheduled_at} · {body.agenda[:120]}")
        return _hearing_payload(c, hid)


def _default_participants(c, case_id):
    parts = []
    for p in c.execute("SELECT id, name, role FROM parties WHERE case_id=?", (case_id,)):
        parts.append(ParticipantIn(party_id=p["id"], name=p["name"], role=p["role"]))
    return parts


def _hearing_payload(c, hearing_id):
    h = c.execute("SELECT * FROM hearings WHERE id=?", (hearing_id,)).fetchone()
    d = dict(h)
    d["participants"] = [dict(p) for p in c.execute(
        "SELECT id, name, role, user_id, party_id, invited, attended FROM hearing_participants WHERE hearing_id=?", (hearing_id,))]
    d["notes"] = [_note_dict(r) for r in c.execute("SELECT * FROM hearing_notes WHERE hearing_id=? ORDER BY id", (hearing_id,))]
    return d


def _note_dict(r):
    import json
    d = dict(r)
    d["body"] = json.loads(d.pop("body_json") or "{}")
    return d


@hearing_router.get("/{hearing_id}")
def get_hearing(hearing_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        _hearing(c, hearing_id, user)
        return _hearing_payload(c, hearing_id)


@hearing_router.patch("/{hearing_id}")
def patch_hearing(hearing_id: int, body: HearingPatch, user: dict = Depends(get_current_user)):
    if user["role"] not in STAFF:
        raise HTTPException(403, f"ROLE {user['role']} MAY NOT MODIFY HEARINGS")
    with db() as c:
        h = _hearing(c, hearing_id, user)
        updates, args = [], []
        for field in ("scheduled_at", "duration_min", "agenda", "status"):
            v = getattr(body, field)
            if v is not None:
                if field == "status" and v not in ("SCHEDULED", "RESCHEDULED", "CANCELLED", "COMPLETED", "IN_PROGRESS"):
                    raise HTTPException(422, f"INVALID STATUS: {v}")
                updates.append(f"{field}=?")
                args.append(v)
        if not updates:
            return _hearing_payload(c, hearing_id)
        if body.status == "COMPLETED":
            updates.append("completed_at=?")
            args.append(now_iso())
        args.append(hearing_id)
        c.execute(f"UPDATE hearings SET {', '.join(updates)} WHERE id=?", args)
        action = "HEARING_COMPLETED" if body.status == "COMPLETED" else "HEARING_UPDATED"
        audit.record(c, user, action, case_id=h["case_id"], object_type="hearing", object_id=hearing_id,
                     prev_state=h["status"], new_state=body.status or h["status"], detail="; ".join(updates))
        return _hearing_payload(c, hearing_id)


@hearing_router.post("/{hearing_id}/join")
def join_hearing(hearing_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        h = _hearing(c, hearing_id, user)
        meeting = room_for(h["case_id"], hearing_id)
        c.execute("UPDATE hearing_participants SET attended=1 WHERE hearing_id=? AND user_id=?", (hearing_id, user["id"]))
        sess = c.execute("SELECT * FROM meeting_sessions WHERE hearing_id=? AND status!='ENDED' ORDER BY id DESC LIMIT 1", (hearing_id,)).fetchone()
        if not sess:
            c.execute("INSERT INTO meeting_sessions(hearing_id, provider, room_id, status, started_at) VALUES(?,?,?,?,?)",
                      (hearing_id, meeting.provider, meeting.room_id, "ACTIVE", now_iso()))
            sess = c.execute("SELECT * FROM meeting_sessions WHERE hearing_id=? ORDER BY id DESC LIMIT 1", (hearing_id,)).fetchone()
        c.execute("INSERT INTO meeting_events(session_id, user_id, event, detail, created_at) VALUES(?,?,?,?,?)",
                  (sess["id"], user["id"], "JOINED", "", now_iso()))
        audit.record(c, user, "HEARING_JOINED", case_id=h["case_id"], object_type="hearing", object_id=hearing_id,
                     new_state="IN_PROGRESS", detail=f"joined room {meeting.room_id}")
        return {"meeting": meeting.as_dict(), "hearing": _hearing_payload(c, hearing_id)}


@hearing_router.post("/{hearing_id}/notes", status_code=201)
def add_note(hearing_id: int, body: NotesIn, user: dict = Depends(get_current_user)):
    if user["role"] not in STAFF:
        raise HTTPException(403, f"ROLE {user['role']} MAY NOT RECORD HEARING NOTES")
    import json
    with db() as c:
        h = _hearing(c, hearing_id, user)
        structured = body.model_dump()
        if not any(structured.values()):
            raise HTTPException(422, "A NOTE CANNOT BE EMPTY")
        cur = c.execute("INSERT INTO hearing_notes(hearing_id, author_id, body_json, created_at) VALUES(?,?,?,?)",
                        (hearing_id, user["id"], json.dumps(structured), now_iso()))
        audit.record(c, user, "HEARING_NOTE_RECORDED", case_id=h["case_id"], object_type="hearing_note",
                     object_id=cur.lastrowid, new_state="RECORDED", detail=body.issue[:160])
        return _note_dict(c.execute("SELECT * FROM hearing_notes WHERE id=?", (cur.lastrowid,)).fetchone())


@hearing_router.get("/{hearing_id}/notes")
def get_notes(hearing_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        _hearing(c, hearing_id, user)
        return [_note_dict(r) for r in c.execute("SELECT * FROM hearing_notes WHERE hearing_id=? ORDER BY id", (hearing_id,))]
