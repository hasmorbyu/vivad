"""Audit trail: every state-changing action is recorded as a chained audit event.

Callers pass the acting user (a dict from auth) or None for system actions. The audit
event is written in the same transaction as the change it describes.
"""
from .ledger import append_audit, now_iso  # noqa: F401  (now_iso re-exported for services)


def record(conn, user, action: str, *, case_id=None, object_type="", object_id="",
           prev_state="", new_state="", detail="") -> str:
    return append_audit(
        conn,
        case_id=case_id,
        actor_id=user["id"] if user else None,
        actor_role=user["role"] if user else "SYSTEM",
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id is not None else "",
        prev_state=prev_state if isinstance(prev_state, str) else str(prev_state),
        new_state=new_state if isinstance(new_state, str) else str(new_state),
        detail=detail,
    )
