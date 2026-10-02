"""Case timeline progression model.

Builds a chronological, structural model of the case journey from the real case data
(parties, statements, evidence, analysis, contradictions, reviews, requests, hearings,
decision). The frontend renders this one model either as a horizontal journey map or, on
narrow screens, as a vertical progression — the model never changes with the viewport.

Each stage carries a positional status (COMPLETED -> CURRENT -> UPCOMING) plus an optional
condition flag (BLOCKED, CRITICAL). Nothing here is decorative: stages come from records.
"""
from datetime import datetime, timezone

from ..domain import CATEGORY_LABELS, DECISION_LABELS
from ..parsers.common import IST
from ..services import case_row, parse_json

# case stage -> stage kind
STAGE_KIND = {
    "INTAKE": "FILED",
    "PARTIES": "PARTIES",
    "STATEMENTS": "STATEMENTS",
    "EVIDENCE": "EVIDENCE_SUBMITTED",
    "PROCESSING": "EVIDENCE_SUBMITTED",
    "ANALYSIS": "ANALYSIS",
    "HUMAN_REVIEW": "HUMAN_REVIEW",
    "EVIDENCE_REQUESTS": "EVIDENCE_REQUEST",
    "HEARING": "HEARING",
    "DECISION": "DECISION",
    "CLOSED": "RESOLUTION",
}

# Procedural sequence. The journey reads by stage order first and date second, so a later
# administrative re-run never reorders the story of the case.
KIND_ORDER = {
    "FILED": 0, "PARTIES": 1, "STATEMENTS": 2, "EVIDENCE_SUBMITTED": 3, "ANALYSIS": 4,
    "CONTRADICTIONS": 5, "HUMAN_REVIEW": 6, "EVIDENCE_REQUEST": 7, "HEARING": 8,
    "DECISION": 9, "RESOLUTION": 10,
}

EVIDENCE_LABEL = {
    "DOCUMENT": "Documents", "SPREADSHEET": "Records", "STRUCTURED": "Data files",
    "EMAIL": "Emails", "CHAT": "Messages", "IMAGE": "Images", "AUDIO": "Audio",
    "VIDEO": "Video", "UNKNOWN": "Files",
}


def _dt(value):
    if not value:
        return None
    s = str(value)
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    # naive times are assumed IST so comparisons against "now" never mix offsets
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt


def _row_dicts(conn, sql, args):
    return [dict(r) for r in conn.execute(sql, args)]


def build_journey(conn, case_id: str) -> dict:
    case = case_row(conn, case_id)
    if not case:
        return {}
    now = datetime.now(timezone.utc).astimezone()

    parties = _row_dicts(conn, "SELECT id, name, role, contact, created_at FROM parties WHERE case_id=? ORDER BY id", (case_id,))
    evidence = _row_dicts(conn,
        "SELECT id, evidence_ref, filename, source_type, status, verify_status, uploaded_at, record_count "
        "FROM evidence WHERE case_id=? ORDER BY id", (case_id,))
    statements = _row_dicts(conn,
        "SELECT s.id, s.submitted_at, p.name, p.role FROM statements s LEFT JOIN parties p ON p.id=s.party_id "
        "WHERE s.case_id=? ORDER BY s.id", (case_id,))
    findings = _row_dicts(conn,
        "SELECT finding_ref, kind, origin, human_status FROM ai_findings WHERE case_id=? ORDER BY finding_ref", (case_id,))
    contradictions = _row_dicts(conn,
        "SELECT contradiction_ref, kind, title, verification_status, evidence_ids, created_at "
        "FROM contradictions WHERE case_id=? ORDER BY contradiction_ref", (case_id,))
    reviews = _row_dicts(conn,
        "SELECT hr.action, hr.created_at, hr.finding_id, u.display_name, u.role FROM human_reviews hr "
        "LEFT JOIN users u ON u.id=hr.reviewer_id WHERE hr.case_id=? ORDER BY hr.id", (case_id,))
    requests = _row_dicts(conn,
        "SELECT id, about, note, status, created_at FROM evidence_requests WHERE case_id=? ORDER BY id", (case_id,))
    hearings = _row_dicts(conn,
        "SELECT id, scheduled_at, duration_min, status, agenda, provider, completed_at FROM hearings WHERE case_id=? ORDER BY scheduled_at", (case_id,))
    decision = conn.execute("SELECT * FROM decisions WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    legal_rows = _row_dicts(conn,
        "SELECT lr.id, lr.act, lr.section, lr.title FROM case_legal_refs clr JOIN legal_references lr ON lr.id=clr.legal_reference_id "
        "WHERE clr.case_id=? ORDER BY clr.id LIMIT 6", (case_id,))

    evidence_by_id = {e["id"]: e for e in evidence}
    evidence_by_ref = {e["evidence_ref"]: e for e in evidence}
    legal_by_id = {r["id"]: {"id": r["id"], "act": r["act"], "section": r["section"], "title": r["title"]} for r in legal_rows}

    def ev_public(e):
        return {"id": e["id"], "evidence_ref": e["evidence_ref"], "filename": e["filename"], "source_type": e["source_type"]}

    stages: list[dict] = []

    def add(kind, title, subtitle, date, *, description="", participants=None, evidence_items=None,
            legal=None, action_required="", due_date="", source="", record_ref="", related=None, flag=None, flag_reason=""):
        stages.append({
            "id": f"{kind}-{len(stages)}", "kind": kind, "title": title, "subtitle": subtitle,
            "description": description, "date": date, "participants": participants or [],
            "evidence": evidence_items or [], "legalReferences": legal or [],
            "documents": [ev_public(e) for e in (evidence_items or [])],
            "actionRequired": action_required, "dueDate": due_date, "source": source, "recordRef": record_ref,
            "relatedEvents": related or [], "flag": flag, "flagReason": flag_reason,
        })

    # 1. filed
    add("FILED", "Case Filed", "Dispute registered with VIVAD", case["created_at"],
        description=case.get("description") or f"{CATEGORY_LABELS.get(case.get('category'), 'Dispute')}",
        participants=parties, source="case", record_ref=case_id)

    # 2. parties
    if parties:
        add("PARTIES", "Parties Recorded", f"{len(parties)} parties to the dispute",
            min((p["created_at"] for p in parties if p["created_at"]), default=case["created_at"]),
            participants=parties, source="parties")

    # 3. statements
    if statements:
        seen = {}
        for s in statements:
            if s["name"] and s["name"] not in seen:
                seen[s["name"]] = {"name": s["name"], "role": s["role"]}
        add("STATEMENTS", "Statements Submitted", f"{len(statements)} statement(s) captured",
            min((s["submitted_at"] for s in statements if s["submitted_at"]), default=case["created_at"]),
            participants=list(seen.values()), source="statements")

    # 4. evidence submitted (with branch groups by type)
    if evidence:
        groups: dict[str, list] = {}
        for e in evidence:
            groups.setdefault(e["source_type"] or "UNKNOWN", []).append(e)
        mismatch = [e["evidence_ref"] for e in evidence if e["verify_status"] == "MISMATCH"]
        add("EVIDENCE_SUBMITTED", "Evidence Submitted", f"{len(evidence)} file(s) received and hashed",
            min((e["uploaded_at"] for e in evidence if e["uploaded_at"]), default=case["created_at"]),
            participants=parties, evidence_items=evidence, source="evidence",
            flag="CRITICAL" if mismatch else None,
            flag_reason=f"Integrity mismatch detected for {', '.join(mismatch)}" if mismatch else "")
        stages[-1]["branches"] = [
            {"id": f"BR-{type_}", "label": EVIDENCE_LABEL.get(type_, type_), "count": len(items),
             "evidence": [ev_public(e) for e in items]}
            for type_, items in sorted(groups.items())
        ]

    # 5. analysis
    if case["analysis_state"] == "DONE" or findings:
        date = case.get("analysis_at") or max((e["uploaded_at"] or case["created_at"] for e in evidence), default=case["created_at"])
        add("ANALYSIS", "Analysis Prepared", f"{len(findings)} finding(s); {len(legal_rows)} legal reference(s)",
            date, description="Claims extracted, evidence linked, timeline and findings generated.",
            legal=legal_rows, source="analysis", record_ref=case.get("summary_source") or "")

    # 6. contradictions
    if contradictions:
        cited = []
        for c in contradictions:
            for eid in parse_json(c["evidence_ids"], []):
                if eid in evidence_by_id and evidence_by_id[eid] not in cited:
                    cited.append(evidence_by_id[eid])
        unresolved = [c["contradiction_ref"] for c in contradictions if c["verification_status"] == "REQUIRES_HUMAN_REVIEW"]
        add("CONTRADICTIONS", "Potential Contradictions", f"{len(contradictions)} flagged for human review",
            max((c["created_at"] or case["created_at"] for c in contradictions), default=case["created_at"]),
            description="Inconsistencies between statements and evidence identified for verification.",
            evidence_items=cited, legal=legal_rows, source="contradictions",
            flag="CRITICAL" if unresolved else None,
            flag_reason=f"{len(unresolved)} contradiction(s) still require human review" if unresolved else "")
        stages[-1]["relatedEvents"] = [{"id": c["contradiction_ref"], "title": c["title"]} for c in contradictions]

    # 7. human review
    if reviews:
        seen = {}
        for r in reviews:
            if r["display_name"] and r["display_name"] not in seen:
                seen[r["display_name"]] = {"name": r["display_name"], "role": r["role"]}
        accepted = sum(1 for r in reviews if r["action"] in ("ACCEPT", "EDIT"))
        rejected = sum(1 for r in reviews if r["action"] in ("REJECT", "MARK_UNRESOLVED"))
        add("HUMAN_REVIEW", "Human Review", f"{accepted} accepted · {rejected} rejected / unresolved",
            min((r["created_at"] for r in reviews if r["created_at"]), default=case["created_at"]),
            participants=list(seen.values()), source="reviews")

    # 8. evidence requests
    for req in requests:
        open_ = req["status"] == "OPEN"
        add("EVIDENCE_REQUEST", "Additional Evidence Requested", req["about"],
            req["created_at"], description=req["note"] or "Awaiting material from a party.",
            action_required=req["about"], source="evidence_requests", record_ref=str(req["id"]),
            flag="BLOCKED" if open_ else None,
            flag_reason="Progression waits on this material." if open_ else "")

    # 9. hearings
    for h in hearings:
        parts = _row_dicts(conn, "SELECT name, role, attended FROM hearing_participants WHERE hearing_id=? ORDER BY id", (h["id"],))
        completed = h["status"] == "COMPLETED"
        hdt = _dt(h["scheduled_at"])
        missed = (not completed) and hdt is not None and hdt < now
        title = "Hearing Held" if completed else "Hearing Scheduled"
        add("HEARING", title, h["agenda"] or "Hearing", h["scheduled_at"],
            description=f"{h['duration_min']} minute hearing · {h['provider']} room.", participants=parts,
            source="hearings", record_ref=str(h["id"]),
            flag="CRITICAL" if missed else None,
            flag_reason="Scheduled time has passed and the hearing is not marked complete." if missed else "")

    # 10. decision
    if decision:
        d = dict(decision)
        legal = [legal_by_id[i] for i in parse_json(d["legal_refs"], []) if i in legal_by_id]
        # decision stores evidence *references* (E-001), not database ids
        cited = [evidence_by_ref[r] for r in parse_json(d["evidence_ids"], []) if r in evidence_by_ref]
        maker = conn.execute("SELECT display_name, role FROM users WHERE id=?", (d["decided_by"],)).fetchone()
        add("DECISION", "Decision Recorded", DECISION_LABELS.get(d["status"], d["status"]),
            d["decided_at"], description=d["decision"], participants=([{"name": maker["display_name"], "role": maker["role"]}] if maker else []),
            evidence_items=cited, legal=legal, source="decision", record_ref=d["decision_ref"])

    # 11. upcoming resolution (only when no decision yet)
    if not decision:
        add("RESOLUTION", "Human Decision", "Awaiting authorised decision", "",
            description="A chair records a preliminary, non-binding resolution. AI never decides.",
            action_required=case.get("next_action") or "Human review required", source="case",
            due_date="", related=[])

    # ---- status assignment
    ordered = [s for s in stages if s["date"] or s["kind"] == "RESOLUTION"]
    ordered.sort(key=lambda s: (KIND_ORDER.get(s["kind"], 99), s["date"] or "9999", stages.index(s)))
    closed = decision is not None or case["status"] in ("RESOLVED", "CLOSED", "ESCALATED")
    mapped = STAGE_KIND.get(case.get("current_stage") or "", None)
    current_idx = None
    for idx, s in enumerate(ordered):
        if mapped and s["kind"] == mapped:
            current_idx = idx
    if closed and ordered:
        current_idx = len(ordered) - 1
    if current_idx is None:
        current_idx = max(0, len(ordered) - 1)

    for idx, s in enumerate(ordered):
        s["status"] = "COMPLETED" if idx < current_idx else "CURRENT" if idx == current_idx else "UPCOMING"
        s["lane"] = idx % 2
        s["index"] = idx
        s["total"] = len(ordered)
        if s["status"] == "UPCOMING":
            # an unmet condition on a future stage is pending, not blocked
            if s.get("flag") == "BLOCKED":
                s["flagReason"] = s.get("flagReason") or "Awaiting required material."

    counts = {
        "completed": sum(1 for s in ordered if s["status"] == "COMPLETED"),
        "current": sum(1 for s in ordered if s["status"] == "CURRENT"),
        "upcoming": sum(1 for s in ordered if s["status"] == "UPCOMING"),
    }
    due = next((s["dueDate"] for s in ordered if s["status"] == "UPCOMING" and s.get("dueDate")), "")
    return {
        "case": {"id": case["id"], "title": case["title"], "category": case["category"],
                 "category_label": CATEGORY_LABELS.get(case.get("category"), "Dispute"),
                 "status": case["status"], "stage": case["current_stage"], "synthetic": case["synthetic"]},
        "header": {
            "case_id": case["id"],
            "current_stage": next((s["title"] for s in ordered if s["status"] == "CURRENT"), case["current_stage"]),
            "next_action": case.get("next_action") or "",
            "due_date": due,
            "counts": counts,
        },
        "stages": ordered,
    }
