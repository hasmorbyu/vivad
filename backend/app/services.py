"""Shared read models used by API routes and generated reports."""
import json

from .domain import CASE_STATUSES, CLASSIFICATIONS


def row_to_dict(row) -> dict | None:
    return dict(row) if row else None


def case_row(conn, case_id: str) -> dict | None:
    return row_to_dict(conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone())


def case_stats(conn, case_id: str) -> dict:
    q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]  # noqa: E731
    return {
        "parties": q("SELECT COUNT(*) FROM parties WHERE case_id=?", case_id),
        "statements": q("SELECT COUNT(*) FROM statements WHERE case_id=?", case_id),
        "evidence": q("SELECT COUNT(*) FROM evidence WHERE case_id=?", case_id),
        "evidence_verified": q("SELECT COUNT(*) FROM evidence WHERE case_id=? AND verify_status='VERIFIED'", case_id),
        "claims": q("SELECT COUNT(*) FROM claims WHERE case_id=?", case_id),
        "events": q("SELECT COUNT(*) FROM events WHERE case_id=?", case_id),
        "issues": q("SELECT COUNT(*) FROM issues WHERE case_id=?", case_id),
        "contradictions": q("SELECT COUNT(*) FROM contradictions WHERE case_id=?", case_id),
        "contradictions_open": q("SELECT COUNT(*) FROM contradictions WHERE case_id=? AND verification_status='REQUIRES_HUMAN_REVIEW'", case_id),
        "legal_refs": q("SELECT COUNT(*) FROM case_legal_refs WHERE case_id=?", case_id),
        "hearings": q("SELECT COUNT(*) FROM hearings WHERE case_id=?", case_id),
        "ai_findings": q("SELECT COUNT(*) FROM ai_findings WHERE case_id=?", case_id),
        "ai_findings_pending": q("SELECT COUNT(*) FROM ai_findings WHERE case_id=? AND human_status='PENDING'", case_id),
        "decisions": q("SELECT COUNT(*) FROM decisions WHERE case_id=?", case_id),
        "audit_events": q("SELECT COUNT(*) FROM audit_events WHERE case_id=?", case_id),
    }


def case_brief(conn, row: dict, with_stats: bool = True) -> dict:
    d = dict(row)
    d.pop("analysis_json", None)
    parties = [dict(p) for p in conn.execute(
        "SELECT id, name, role FROM parties WHERE case_id=? ORDER BY id", (row["id"],))]
    d["parties"] = parties
    d["party_summary"] = " vs ".join(p["name"] for p in parties[:2]) if parties else ""
    if with_stats:
        d["stats"] = case_stats(conn, row["id"])
    return d


def dashboard_metrics(conn) -> dict:
    q = lambda sql, *a: conn.execute(sql, a).fetchone()[0]  # noqa: E731
    return {
        "active_cases": q("SELECT COUNT(*) FROM cases WHERE status NOT IN ('CLOSED','RESOLVED','ESCALATED')"),
        "awaiting_review": q("SELECT COUNT(*) FROM cases WHERE status IN ('AWAITING_REVIEW','AWAITING_COMMITTEE_REVIEW')"),
        "hearings_scheduled": q("SELECT COUNT(*) FROM hearings WHERE status='SCHEDULED'"),
        "evidence_pending": q("SELECT COUNT(*) FROM evidence WHERE status NOT IN ('PARSED','ERROR','SKIPPED')"),
        "requiring_validation": q("SELECT COUNT(DISTINCT case_id) FROM ai_findings WHERE human_status='PENDING'"),
        "resolved_closed": q("SELECT COUNT(*) FROM cases WHERE status IN ('RESOLVED','CLOSED')"),
    }


def classification_ui(conn, classification: str) -> dict:
    sym, label, full = CLASSIFICATIONS.get(classification, ("[?]", "UNRESOLVED", "UNRESOLVED"))
    return {"symbol": sym, "label": label, "full": full}


def next_action_text(conn, case_row: dict) -> str:
    status = case_row["status"]
    mapping = {
        "INTAKE": "Complete intake and add parties",
        "AWAITING_RESPONSE": "Awaiting respondent statement",
        "PROCESSING": "Evidence processing",
        "AWAITING_REVIEW": "Human review of AI findings",
        "AWAITING_COMMITTEE_REVIEW": "Committee review of validated case",
        "EVIDENCE_REQUESTED": "Additional evidence requested",
        "HEARING_SCHEDULED": "Hearing scheduled",
        "AWAITING_DECISION": "Human decision required",
        "RESOLVED": "Resolution recorded",
        "ESCALATED": "Referred to appropriate authority",
        "CLOSED": "Case closed",
    }
    return mapping.get(status, "Review case")


def parse_json(value, default):
    try:
        return json.loads(value) if value not in (None, "") else default
    except (json.JSONDecodeError, TypeError):
        return default


def evidence_rows(conn, case_id: str) -> list[dict]:
    return [dict(r) for r in conn.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id", (case_id,))]


def evidence_detail(conn, case_id: str, evidence_id: int) -> dict | None:
    r = conn.execute("SELECT * FROM evidence WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
    if not r:
        return None
    d = dict(r)
    d.pop("stored_path", None)
    d["extracted"] = parse_json(d.pop("extracted_json", None), {"entities": [], "amounts": [], "dates": []})
    ref = d["evidence_ref"]
    d["related_party"] = None
    if d["related_party_id"]:
        p = conn.execute("SELECT id, name, role FROM parties WHERE id=?", (d["related_party_id"],)).fetchone()
        d["related_party"] = dict(p) if p else None
    d["related_claims"] = [dict(x) for x in conn.execute(
        "SELECT cl.claim_ref, cl.text, cl.status, er.relationship, cl.id FROM evidence_references er "
        "JOIN claims cl ON cl.id=er.claim_id WHERE er.evidence_id=?", (evidence_id,))]
    d["related_events"] = [dict(x) for x in conn.execute(
        "SELECT event_ref, event_time, title, event_type FROM events WHERE evidence_id=? ORDER BY event_time", (evidence_id,))]
    d["related_contradictions"] = [dict(x) for x in conn.execute(
        "SELECT contradiction_ref, kind, title, verification_status FROM contradictions WHERE case_id=? AND evidence_ids LIKE ?",
        (case_id, f'%"{evidence_id}"%'))]
    d["related_legal"] = [dict(x) for x in conn.execute(
        "SELECT legal_reference_id, relevance FROM case_legal_refs WHERE case_id=? LIMIT 20", (case_id,))]
    d["audit_history"] = [dict(x) for x in conn.execute(
        "SELECT action, actor_role, new_state, detail, created_at, record_hash FROM audit_events "
        "WHERE case_id=? AND object_type='evidence' AND object_id=? ORDER BY seq", (case_id, ref))]
    d["integrity"] = [dict(x) for x in conn.execute(
        "SELECT kind, object_hash, record_hash, anchor_status, created_at FROM integrity_records "
        "WHERE case_id=? AND object_type='evidence' AND object_id=? ORDER BY seq", (case_id, ref))]
    d["related_evidence"] = [dict(x) for x in conn.execute(
        "SELECT DISTINCT e2.evidence_ref, e2.filename FROM evidence_references er1 "
        "JOIN evidence_references er2 ON er2.claim_id=er1.claim_id AND er2.evidence_id!=er1.evidence_id "
        "JOIN evidence e2 ON e2.id=er2.evidence_id WHERE er1.evidence_id=?", (evidence_id,))]
    return d
