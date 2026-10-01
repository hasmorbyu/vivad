"""Append-only, hash-chained ledger for audit events and integrity anchors.

Each row stores the hash of the previous row and its own record hash computed over the
canonical payload, so removing or altering any row breaks the chain and is detectable.
Only hashes are stored for anchored objects; no case data ever leaves the database.
"""
from datetime import datetime, timezone

from .integrity import chain_hash

AUDIT_COLS = ("seq", "case_id", "actor_id", "actor_role", "action", "object_type", "object_id",
              "prev_state", "new_state", "detail", "created_at")
INTEGRITY_COLS = ("seq", "case_id", "kind", "object_type", "object_id", "object_hash", "created_at")


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _tail(conn, table):
    row = conn.execute(f"SELECT seq, record_hash FROM {table} ORDER BY seq DESC LIMIT 1").fetchone()
    return (row["seq"], row["record_hash"]) if row else (0, "")


def _payload(cols, values) -> dict:
    return {c: values.get(c) for c in cols}


def append_audit(conn, *, case_id, actor_id, actor_role, action, object_type="", object_id="",
                 prev_state="", new_state="", detail="") -> str:
    seq, prev_hash = _tail(conn, "audit_events")
    seq += 1
    ts = now_iso()
    values = {"seq": seq, "case_id": case_id, "actor_id": actor_id, "actor_role": actor_role,
              "action": action, "object_type": object_type, "object_id": object_id,
              "prev_state": prev_state, "new_state": new_state, "detail": detail, "created_at": ts}
    record_hash = chain_hash(prev_hash, _payload(AUDIT_COLS, values))
    conn.execute(
        "INSERT INTO audit_events(seq, case_id, actor_id, actor_role, action, object_type, object_id,"
        " prev_state, new_state, detail, created_at, prev_hash, record_hash) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (seq, case_id, actor_id, actor_role, action, object_type, object_id, prev_state, new_state, detail, ts, prev_hash, record_hash))
    return record_hash


def append_integrity(conn, *, case_id, kind, object_type, object_id, object_hash,
                     anchor_status="LOCAL_ONLY", anchor_ref="") -> str:
    seq, prev_hash = _tail(conn, "integrity_records")
    seq += 1
    ts = now_iso()
    values = {"seq": seq, "case_id": case_id, "kind": kind, "object_type": object_type,
              "object_id": object_id, "object_hash": object_hash, "created_at": ts}
    record_hash = chain_hash(prev_hash, _payload(INTEGRITY_COLS, values))
    conn.execute(
        "INSERT INTO integrity_records(seq, case_id, kind, object_type, object_id, object_hash, prev_hash, record_hash,"
        " anchor_status, anchor_ref, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (seq, case_id, kind, object_type, object_id, object_hash, prev_hash, record_hash, anchor_status, anchor_ref, ts))
    return record_hash


def verify_audit_chain(conn) -> dict:
    prev_hash = ""
    seq_expected = 1
    for r in conn.execute("SELECT * FROM audit_events ORDER BY seq"):
        d = dict(r)
        if d["seq"] != seq_expected or d["prev_hash"] != prev_hash:
            return {"ok": False, "broken_at": d["seq"], "reason": "LINK MISMATCH"}
        if chain_hash(prev_hash, _payload(AUDIT_COLS, d)) != d["record_hash"]:
            return {"ok": False, "broken_at": d["seq"], "reason": "RECORD HASH MISMATCH"}
        prev_hash = d["record_hash"]
        seq_expected += 1
    return {"ok": True, "events": seq_expected - 1, "head": prev_hash}


def verify_integrity_chain(conn) -> dict:
    prev_hash = ""
    seq_expected = 1
    for r in conn.execute("SELECT * FROM integrity_records ORDER BY seq"):
        d = dict(r)
        if d["seq"] != seq_expected or d["prev_hash"] != prev_hash:
            return {"ok": False, "broken_at": d["seq"], "reason": "LINK MISMATCH"}
        if chain_hash(prev_hash, _payload(INTEGRITY_COLS, d)) != d["record_hash"]:
            return {"ok": False, "broken_at": d["seq"], "reason": "RECORD HASH MISMATCH"}
        prev_hash = d["record_hash"]
        seq_expected += 1
    return {"ok": True, "records": seq_expected - 1, "head": prev_hash}
