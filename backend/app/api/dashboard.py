"""Dashboard metrics and the role-scoped case queue."""
from fastapi import APIRouter, Depends

from ..auth import STAFF_ROLES, get_current_user
from ..db import db
from ..services import case_brief, dashboard_metrics, next_action_text

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: dict = Depends(get_current_user)):
    with db() as c:
        if user["role"] in STAFF_ROLES:
            rows = [dict(r) for r in c.execute("SELECT * FROM cases ORDER BY created_at DESC LIMIT 100")]
        else:
            rows = [dict(r) for r in c.execute(
                "SELECT DISTINCT c.* FROM cases c LEFT JOIN parties p ON p.case_id=c.id "
                "WHERE c.created_by=? OR p.user_id=? ORDER BY c.created_at DESC LIMIT 100",
                (user["id"], user["id"]))]
        queue = []
        for r in rows:
            brief = case_brief(c, r)
            brief["next_action"] = r["next_action"] or next_action_text(c, r)
            queue.append(brief)
        return {"metrics": dashboard_metrics(c), "cases": queue}
