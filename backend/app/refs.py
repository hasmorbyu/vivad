"""Human-readable reference allocation (E-001, CL-001, C-001, IS-01, EV-001, F-001, D-001).

Counters are per case and allocated inside the caller's transaction so references are
stable and never reused. All identifiers are produced by deterministic code, never by AI.
"""
from .ledger import now_iso


def next_ref(conn, case_id: str, kind: str, prefix: str, width: int = 3) -> str:
    key = f"{case_id}:{kind}"
    row = conn.execute("SELECT value FROM counters WHERE name=?", (key,)).fetchone()
    value = (row["value"] if row else 0) + 1
    if row:
        conn.execute("UPDATE counters SET value=? WHERE name=?", (value, key))
    else:
        conn.execute("INSERT INTO counters(name, value) VALUES(?,?)", (key, value))
    return f"{prefix}-{value:0{width}d}"


def reset_counter(conn, case_id: str, kind: str) -> None:
    """Reset a per-case counter before a full rebuild so references stay stable on re-run."""
    conn.execute("DELETE FROM counters WHERE name=?", (f"{case_id}:{kind}",))


def touch(conn, case_id: str) -> None:
    conn.execute("UPDATE cases SET updated_at=? WHERE id=?", (now_iso(), case_id))
