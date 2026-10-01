"""Timeline construction.

Events are drawn from evidence records that carry a time and a substantive fact (amount,
date, document identifier), plus the submission of each statement. Every event points back
to its evidence and record; date-only events stay date-only.
"""
from ..nlp import extract_facts
from ..refs import next_ref, reset_counter, touch

MAX_PER_EVIDENCE = 40


def _salient(raw: str) -> bool:
    f = extract_facts(raw)
    return bool(f["amounts"] or f["dates"] or any(e["type"] == "DOCUMENT_ID" for e in f["entities"]))


def _title(raw: str) -> str:
    f = extract_facts(raw)
    bits = []
    if f["amounts"]:
        bits.append(f"₹{f['amounts'][0]:,.0f}")
    if f["dates"]:
        bits.append(f["dates"][0]["value"])
    return " · ".join(bits) if bits else raw.strip()[:60]


def _when(event_time, raw: str):
    """Prefer a parsed record time; otherwise accept a date stated inline (stays date-only)."""
    if event_time:
        return event_time, ("date" if len(event_time) == 10 else "second")
    facts = extract_facts(raw or "")
    if facts["dates"]:
        return facts["dates"][0]["iso"][:10], "date"
    return None, None


def build_timeline(conn, case_id: str) -> dict:
    conn.execute("DELETE FROM events WHERE case_id=?", (case_id,))
    reset_counter(conn, case_id, "event")
    evidence_events = []
    counts: dict[int, int] = {}
    for r in conn.execute(
        "SELECT r.ref, r.record_type, r.event_time, r.raw_text, ev.id evidence_id "
        "FROM records r JOIN evidence ev ON ev.id=r.evidence_id WHERE r.case_id=? ORDER BY r.event_time",
        (case_id,)):
        when, precision = _when(r["event_time"], r["raw_text"])
        if not when or not _salient(r["raw_text"]):
            continue
        eid = r["evidence_id"]
        counts[eid] = counts.get(eid, 0) + 1
        if counts[eid] > MAX_PER_EVIDENCE:
            continue
        evidence_events.append({"when": when, "precision": precision, "title": _title(r["raw_text"]),
                                "desc": r["raw_text"][:220], "evidence_id": eid, "record_ref": r["ref"],
                                "event_type": r["record_type"]})

    statement_events = []
    for st in conn.execute(
        "SELECT s.*, p.name party_name FROM statements s LEFT JOIN parties p ON p.id=s.party_id WHERE s.case_id=? ORDER BY s.id",
        (case_id,)):
        if not st["submitted_at"]:
            continue
        desc = (st["claim"] or st["what"] or "Statement submitted")[:220]
        statement_events.append({"when": st["submitted_at"][:10], "precision": "date",
                                 "title": f"Statement — {st['party_name'] or 'party'}", "desc": desc,
                                 "evidence_id": None, "record_ref": None, "event_type": "STATEMENT"})

    all_events = evidence_events + statement_events
    all_events.sort(key=lambda e: (e["when"], e["title"]))
    seen = set()
    created = 0
    for e in all_events:
        key = (e["when"], e["desc"])
        if key in seen:
            continue
        seen.add(key)
        ref = next_ref(conn, case_id, "event", "EV")
        conn.execute(
            "INSERT INTO events(case_id, event_ref, event_time, time_precision, title, description, event_type, evidence_id, record_ref, origin, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, ref, e["when"], e["precision"], e["title"], e["desc"], e["event_type"], e["evidence_id"],
             e["record_ref"], "EVIDENCE" if e["evidence_id"] else "STATEMENT", e["when"]))
        created += 1
    touch(conn, case_id)
    return {"events": created}
