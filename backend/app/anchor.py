"""Integrity anchoring adapter.

The local ledger is append-only and hash-chained. If a chain is configured, only the head
hash would ever be published — never case data or evidence. Anchoring is optional and the
UI states plainly whether an external anchor exists.
"""
from .config import get_settings


def anchor_head(conn) -> dict:
    head = conn.execute("SELECT record_hash, seq FROM integrity_records ORDER BY seq DESC LIMIT 1").fetchone()
    if not head:
        return {"status": "EMPTY", "note": "No integrity records yet.", "head": None, "head_seq": 0}
    s = get_settings()
    if not (s.blockchain_rpc_url and s.blockchain_private_key):
        return {"status": "LOCAL_ONLY", "head": head["record_hash"], "head_seq": head["seq"],
                "note": "No external chain configured. The ledger is local, append-only and hash-chained."}
    # A real implementation would submit only this head hash to the configured chain.
    return {"status": "NOT_PUBLISHED", "head": head["record_hash"], "head_seq": head["seq"],
            "note": "A chain is configured but publishing is not enabled in this build. Only the head hash would ever be sent."}
