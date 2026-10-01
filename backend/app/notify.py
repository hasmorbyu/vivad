"""In-app notifications. Email/SMS are out of scope; this is the notification architecture."""
from .ledger import now_iso


def notify(conn, *, case_id: str | None, user_id: int | None, kind: str, title: str, body: str = "") -> int:
    cur = conn.execute(
        "INSERT INTO notifications(case_id, user_id, kind, title, body, read, created_at) VALUES(?,?,?,?,?,0,?)",
        (case_id, user_id, kind, title, body, now_iso()))
    return cur.lastrowid


def notify_case_parties(conn, case_id: str, kind: str, title: str, body: str = "", exclude_user=None) -> int:
    n = 0
    for p in conn.execute("SELECT user_id FROM parties WHERE case_id=? AND user_id IS NOT NULL", (case_id,)):
        if exclude_user and p["user_id"] == exclude_user:
            continue
        notify(conn, case_id=case_id, user_id=p["user_id"], kind=kind, title=title, body=body)
        n += 1
    return n
