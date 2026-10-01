"""Global search across cases the user may access, plus the public legal-reference dataset."""
from fastapi import APIRouter, Depends, Query

from ..auth import STAFF_ROLES, get_current_user
from ..db import db

router = APIRouter(prefix="/api/search", tags=["search"])


def _accessible(conn, user) -> list[str]:
    if user["role"] in STAFF_ROLES:
        return [r[0] for r in conn.execute("SELECT id FROM cases")]
    rows = conn.execute(
        "SELECT id FROM cases WHERE created_by=? UNION SELECT case_id FROM parties WHERE user_id=?",
        (user["id"], user["id"]))
    return [r[0] for r in rows]


def _in(ids):
    return ",".join("?" * len(ids)) if ids else "NULL"


@router.get("")
def search(q: str = Query(min_length=2, max_length=120), user: dict = Depends(get_current_user)):
    like = f"%{q}%"
    with db() as c:
        ids = _accessible(c, user)
        ph = _in(ids)
        out = {}
        out["cases"] = [{"id": r["id"], "title": r["title"], "status": r["status"], "category": r["category"]}
                        for r in c.execute(f"SELECT id, title, status, category FROM cases WHERE id IN ({ph}) AND (id LIKE ? OR title LIKE ? OR description LIKE ?) LIMIT 20", (*ids, like, like, like))] if ids else []
        out["parties"] = [{"case_id": r["case_id"], "name": r["name"], "role": r["role"]}
                          for r in c.execute(f"SELECT case_id, name, role FROM parties WHERE case_id IN ({ph}) AND (name LIKE ? OR contact LIKE ?) LIMIT 20", (*ids, like, like))] if ids else []
        out["evidence"] = [{"case_id": r["case_id"], "id": r["id"], "evidence_ref": r["evidence_ref"], "filename": r["filename"], "status": r["status"]}
                           for r in c.execute(f"SELECT case_id, id, evidence_ref, filename, status FROM evidence WHERE case_id IN ({ph}) AND (evidence_ref LIKE ? OR filename LIKE ? OR description LIKE ?) LIMIT 20", (*ids, like, like, like))] if ids else []
        out["claims"] = [{"case_id": r["case_id"], "claim_ref": r["claim_ref"], "text": r["text"], "status": r["status"]}
                         for r in c.execute(f"SELECT case_id, claim_ref, text, status FROM claims WHERE case_id IN ({ph}) AND (claim_ref LIKE ? OR text LIKE ?) LIMIT 20", (*ids, like, like))] if ids else []
        out["events"] = [{"case_id": r["case_id"], "event_ref": r["event_ref"], "title": r["title"], "event_time": r["event_time"]}
                         for r in c.execute(f"SELECT case_id, event_ref, title, event_time FROM events WHERE case_id IN ({ph}) AND (event_ref LIKE ? OR title LIKE ? OR description LIKE ?) LIMIT 20", (*ids, like, like, like))] if ids else []
        out["hearings"] = [{"case_id": r["case_id"], "id": r["id"], "scheduled_at": r["scheduled_at"], "agenda": r["agenda"], "status": r["status"]}
                           for r in c.execute(f"SELECT case_id, id, scheduled_at, agenda, status FROM hearings WHERE case_id IN ({ph}) AND (agenda LIKE ? OR scheduled_at LIKE ?) LIMIT 20", (*ids, like, like))] if ids else []
        out["legal"] = [{"id": r["id"], "act": r["act"], "section": r["section"], "title": r["title"]}
                        for r in c.execute("SELECT id, act, section, title FROM legal_references WHERE act LIKE ? OR section LIKE ? OR title LIKE ? OR concepts LIKE ? LIMIT 20",
                                           (like, like, like, like))]
        out["total"] = sum(len(v) for v in out.values() if isinstance(v, list))
        return {"query": q, "results": out}
