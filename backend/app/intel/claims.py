"""Deterministic claim extraction and evidence linking.

Claims come from structured statements. Each claim is matched against evidence-derived
facts (amounts, dates, document identifiers). Status describes the documentary support
only; it is never a legal conclusion and uncertain cases are marked for human review.
"""
import json

from ..nlp import extract_facts
from ..refs import next_ref, reset_counter, touch


def _evidence_facts(conn, case_id: str):
    out = []
    for e in conn.execute("SELECT id, evidence_ref, extracted_json FROM evidence WHERE case_id=? AND status='PARSED'", (case_id,)):
        try:
            data = json.loads(e["extracted_json"] or "{}")
        except json.JSONDecodeError:
            data = {}
        amounts = {round(float(a), 2) for a in data.get("amounts", [])}
        dates = {d.get("iso", "")[:10] for d in data.get("dates", []) if d.get("iso")}
        docs = {ent["canonical"].split(":", 1)[1] for ent in data.get("entities", [])
                if ent.get("type") == "DOCUMENT_ID" and ent.get("canonical")}
        out.append({"id": e["id"], "ref": e["evidence_ref"], "amounts": amounts, "dates": dates, "docs": docs})
    return out


def _match(claim_amount, claim_date, claim_docs, ev) -> tuple[int, str]:
    """Return (score, relationship). score counts matched fact categories."""
    score = 0
    rel = []
    if claim_amount is not None and round(claim_amount, 2) in ev["amounts"]:
        score += 1
        rel.append("amount")
    if claim_date and claim_date[:10] in ev["dates"]:
        score += 1
        rel.append("date")
    if claim_docs & ev["docs"]:
        score += 1
        rel.append("document")
    return score, "+".join(rel) or "contextual"


def extract_claims(conn, case_id: str) -> dict:
    conn.execute("DELETE FROM evidence_references WHERE case_id=?", (case_id,))
    conn.execute("DELETE FROM claims WHERE case_id=?", (case_id,))
    reset_counter(conn, case_id, "claim")
    evidence = _evidence_facts(conn, case_id)
    created = 0
    links = 0
    for st in conn.execute("SELECT * FROM statements WHERE case_id=? ORDER BY id", (case_id,)):
        text = (st["claim"] or st["what"] or "").strip()
        if not text:
            continue
        facts = extract_facts(text)
        amount = round(facts["amounts"][0], 2) if facts["amounts"] else None
        date = facts["dates"][0]["iso"] if facts["dates"] else None
        docs = {ent["canonical"].split(":", 1)[1] for ent in facts["entities"]
                if ent["type"] == "DOCUMENT_ID" and ent.get("canonical")}
        claim_ref = next_ref(conn, case_id, "claim", "CL")
        matched = []
        for ev in evidence:
            score, rel = _match(amount, date, docs, ev)
            if score > 0:
                matched.append((ev, score, rel))
        if amount is not None or date is not None or docs:
            if matched:
                status, extraction = "SUPPORTED", "DETERMINISTIC"
            else:
                status, extraction = "UNSUPPORTED", "DETERMINISTIC"
        elif matched:
            status, extraction = "REQUIRES_HUMAN_REVIEW", "DETERMINISTIC"
        else:
            status, extraction = "REQUIRES_HUMAN_REVIEW", "HUMAN"
        cur = conn.execute(
            "INSERT INTO claims(case_id, claim_ref, party_id, text, date, amount, status, source_statement_id, extraction, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (case_id, claim_ref, st["party_id"], text, date, amount, status, st["id"], extraction,
             st["submitted_at"]))
        claim_id = cur.lastrowid
        created += 1
        for ev, _, rel in sorted(matched, key=lambda x: -x[1])[:5]:
            conn.execute("INSERT INTO evidence_references(case_id, claim_id, evidence_id, relationship, note, created_at) VALUES(?,?,?,?,?,?)",
                         (case_id, claim_id, ev["id"], "SUPPORTS", rel, st["submitted_at"]))
            links += 1
    touch(conn, case_id)
    return {"claims": created, "evidence_links": links}
