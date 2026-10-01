"""Build the structured case report used by both the JSON export and the PDF.

The report separates AI-assisted material from human-validated material explicitly, and
carries its generation timestamp and audit reference.
"""
from datetime import datetime

from ..ledger import verify_audit_chain, verify_integrity_chain, now_iso
from ..services import case_row, parse_json


def build_report(conn, case_id: str) -> dict:
    case = case_row(conn, case_id)

    def rows(sql, *args):
        return [dict(r) for r in conn.execute(sql, args)]

    parties = rows("SELECT name, role, contact, relationship FROM parties WHERE case_id=? ORDER BY id", case_id)
    statements = rows(
        "SELECT s.kind, s.claim, s.what, s.when_text, s.where_text, s.who, s.desired_resolution, s.submitted_at, p.name party_name "
        "FROM statements s LEFT JOIN parties p ON p.id=s.party_id WHERE s.case_id=? ORDER BY s.id", case_id)
    claims = rows("SELECT claim_ref, text, amount, date, status, extraction FROM claims WHERE case_id=? ORDER BY claim_ref", case_id)
    for c in claims:
        c["evidence"] = [x[0] for x in conn.execute(
            "SELECT ev.evidence_ref FROM evidence_references er JOIN evidence ev ON ev.id=er.evidence_id WHERE er.claim_id=(SELECT id FROM claims WHERE claim_ref=? AND case_id=?)",
            (c["claim_ref"], case_id))]
    evidence = rows("SELECT evidence_ref, filename, source_type, file_size, sha256, status, verify_status, uploaded_at, description FROM evidence WHERE case_id=? ORDER BY evidence_ref", case_id)
    events = rows("SELECT event_ref, event_time, time_precision, title, description, event_type, record_ref FROM events WHERE case_id=? ORDER BY event_time", case_id)
    contradictions = rows(
        "SELECT contradiction_ref, kind, title, explanation, confidence, origin, verification_status FROM contradictions WHERE case_id=? ORDER BY contradiction_ref", case_id)
    legal = rows(
        "SELECT lr.act, lr.section, lr.title, lr.source_url, lr.last_verified, clr.relevance FROM case_legal_refs clr "
        "JOIN legal_references lr ON lr.id=clr.legal_reference_id WHERE clr.case_id=? ORDER BY clr.id", case_id)
    hearings = rows(
        "SELECT h.id, h.scheduled_at, h.status, h.agenda, h.provider, h.room_id FROM hearings h WHERE h.case_id=? ORDER BY h.scheduled_at", case_id)
    for h in hearings:
        h["participants"] = rows("SELECT name, role, attended FROM hearing_participants WHERE hearing_id=?", h["id"])
        h["notes"] = rows("SELECT body_json, created_at, author_id FROM hearing_notes WHERE hearing_id=? ORDER BY id", h["id"])
        for n in h["notes"]:
            n["body"] = parse_json(n.pop("body_json"), {})
    findings = rows(
        "SELECT finding_ref, kind, title, body, origin, validation, human_status, evidence_ids FROM ai_findings WHERE case_id=? ORDER BY finding_ref", case_id)
    for f in findings:
        f["evidence_ids"] = parse_json(f["evidence_ids"], [])
    reviews = rows(
        "SELECT hr.action, hr.comment, hr.created_at, hr.edited_body, u.display_name reviewer, u.role reviewer_role "
        "FROM human_reviews hr LEFT JOIN users u ON u.id=hr.reviewer_id WHERE hr.case_id=? ORDER BY hr.id", case_id)
    decision_row = conn.execute("SELECT * FROM decisions WHERE case_id=? ORDER BY id DESC LIMIT 1", (case_id,)).fetchone()
    decision = None
    if decision_row:
        decision = dict(decision_row)
        for k in ("evidence_ids", "legal_refs", "accepted_finding_ids", "rejected_finding_ids"):
            decision[k] = parse_json(decision[k], [])
    audit = rows("SELECT seq, action, actor_role, object_type, object_id, new_state, created_at, record_hash FROM audit_events WHERE case_id=? ORDER BY seq", case_id)
    integrity = rows("SELECT seq, kind, object_type, object_id, object_hash, record_hash, anchor_status, created_at FROM integrity_records WHERE case_id=? ORDER BY seq", case_id)

    return {
        "report_title": "VIVAD CASE REPORT",
        "generated_at": now_iso(),
        "disclaimer": ("VIVAD is an AI-assisted preliminary dispute-resolution aid. It does not decide disputes, "
                       "does not determine liability, and is not a court. AI-assisted material is labelled; every "
                       "decision in this report was made by a human. Verify all legal references against their official sources."),
        "case": case,
        "1_case_overview": {
            "id": case["id"], "title": case["title"], "category": case["category"], "status": case["status"],
            "stage": case["current_stage"], "amount": case["amount"], "currency": case["currency"],
            "location": case["location"], "incident_date": case["incident_date"],
            "description": case["description"], "requested_resolution": case["requested_resolution"],
            "created_at": case["created_at"], "summary": case["summary_text"], "summary_source": case["summary_source"],
        },
        "2_party_statements": {"parties": parties, "statements": statements},
        "3_issues_identified": {"claims": claims, "contradictions": contradictions},
        "4_evidence": evidence,
        "5_evidence_claim_relationships": [{"claim": c["claim_ref"], "evidence": c["evidence"]} for c in claims],
        "6_potential_contradictions": contradictions,
        "7_legal_references": legal,
        "8_hearing_history": hearings,
        "9_ai_assisted_analysis": {"findings": findings, "ai_only": [f for f in findings if f["origin"] == "AI"]},
        "10_human_review": {"reviews": reviews, "validated": [f for f in findings if f["human_status"] in ("ACCEPT", "EDIT")],
                            "rejected": [f for f in findings if f["human_status"] in ("REJECT", "MARK_UNRESOLVED")]},
        "11_human_decision": decision,
        "12_audit_information": {
            "events": audit, "integrity": integrity,
            "audit_chain": verify_audit_chain(conn), "integrity_chain": verify_integrity_chain(conn),
            "evidence_hashes": [{"evidence_ref": e["evidence_ref"], "sha256": e["sha256"], "verify_status": e["verify_status"]} for e in evidence],
            "generated_text": f"Report generated {datetime.now().astimezone().isoformat(timespec='seconds')}",
        },
    }
