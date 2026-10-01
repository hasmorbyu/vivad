"""In-app notifications for the signed-in user."""
from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_current_user
from ..db import db

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(user: dict = Depends(get_current_user)):
    with db() as c:
        rows = [dict(r) for r in c.execute(
            "SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100", (user["id"],))]
        unread = c.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND read=0", (user["id"],)).fetchone()[0]
        return {"unread": unread, "items": rows}


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        row = c.execute("SELECT * FROM notifications WHERE id=? AND user_id=?", (notification_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "NOTIFICATION NOT FOUND")
        c.execute("UPDATE notifications SET read=1 WHERE id=?", (notification_id,))
        return {"ok": True}


@router.post("/read-all")
def mark_all(user: dict = Depends(get_current_user)):
    with db() as c:
        c.execute("UPDATE notifications SET read=1 WHERE user_id=?", (user["id"],))
        return {"ok": True}
