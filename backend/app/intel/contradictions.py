"""Deterministic potential-contradiction detection.

None of these are findings of wrongdoing. Each is a potential inconsistency for an
authorised human to verify. Wording states the inconsistency, never who is right, and
never labels a party dishonest. Confidence is a qualitative evidentiary basis, not a score.
"""
import json
import re

from ..nlp import extract_facts
from ..refs import next_ref, reset_counter

STOP = {"the", "was", "were", "paid", "payment", "should", "that", "this", "with", "from", "have",
        "been", "will", "would", "amount", "total", "security", "full", "part", "only", "towards",
        "into", "onto", "over", "under", "than", "then", "there", "their", "about", "after", "before",
        "said", "says", "states", "stated", "also", "some", "such", "make", "made", "give", "given"}
# Domain nouns that identify the *subject* of a claim even though they are common words.
SUBJECTS = {"deposit", "rent", "rental", "lease", "repair", "damage", "invoice", "receipt", "salary",
            "loan", "refund", "fee", "fees", "charges", "interest", "goods", "service", "possession",
            "handover", "agreement", "deduction", "compensation", "property", "tenant", "landlord"}
WORD = re.compile(r"[A-Za-z][A-Za-z-]{3,}")


def _keywords(text: str) -> set[str]:
    return {w.lower() for w in WORD.findall(text or "") if w.lower() not in STOP or w.lower() in SUBJECTS}


def _claim_features(text: str):
    f = extract_facts(text or "")
    docs = {e["canonical"].split(":", 1)[1] for e in f["entities"] if e["type"] == "DOCUMENT_ID" and e.get("canonical")}
    amounts = {round(a, 2) for a in f["amounts"]}
    dates = {d["iso"][:10] for d in f["dates"] if d.get("iso")}
    return docs, amounts, dates, _keywords(text)


def _evidence_index(conn, case_id):
    idx = []
    for e in conn.execute("SELECT id, evidence_ref, extracted_json FROM evidence WHERE case_id=? AND status='PARSED'", (case_id,)):
        try:
            data = json.loads(e["extracted_json"] or "{}")
        except json.JSONDecodeError:
            data = {}
        idx.append({
            "id": e["id"], "ref": e["evidence_ref"],
            "amounts": {round(float(a), 2) for a in data.get("amounts", [])},
            "docs": {ent["canonical"].split(":", 1)[1] for ent in data.get("entities", [])
                     if ent.get("type") == "DOCUMENT_ID" and ent.get("canonical")},
            "dates": {d.get("iso", "")[:10] for d in data.get("dates", []) if d.get("iso")},
        })
    return idx


def detect_contradictions(conn, case_id: str) -> dict:
    conn.execute("DELETE FROM contradictions WHERE case_id=?", (case_id,))
    reset_counter(conn, case_id, "contradiction")
    claims = [dict(r) for r in conn.execute(
        "SELECT c.*, p.name party_name, p.role party_role FROM claims c LEFT JOIN parties p ON p.id=c.party_id WHERE c.case_id=? ORDER BY c.id",
        (case_id,))]
    evidence = _evidence_index(conn, case_id)
    found: list[dict] = []

    def add(kind, title, a, b, evidence_ids, explanation, basis, origin="DETERMINISTIC"):
        key = (kind, a["id"] if a else None, b["id"] if b else None, explanation)
        if any(f.get("_key") == key for f in found):
            return
        found.append({"_key": key, "kind": kind, "title": title, "a": a, "b": b,
                      "evidence": list(dict.fromkeys(evidence_ids)), "explanation": explanation, "basis": basis, "origin": origin})

    # 1. statement vs documentary evidence for the same document identifier
    for c in claims:
        docs, amounts, _, _ = _claim_features(c["text"])
        for ev in evidence:
            shared = docs & ev["docs"]
            if not shared:
                continue
            if amounts and ev["amounts"] and not (amounts & ev["amounts"]):
                add("STATEMENT_EVIDENCE",
                    "Claimed amount differs from the documentary record",
                    c, None, [ev["id"]],
                    f"{c['claim_ref']} states {_fmt_amounts(amounts)} for {', '.join(sorted(shared))}, "
                    f"while {ev['ref']} records {_fmt_amounts(ev['amounts'])} for the same reference. "
                    "The documents and the statement do not agree on the amount.",
                    "DOCUMENTED")

    # 2. pairwise inconsistencies between claims about a shared subject
    for i in range(len(claims)):
        for j in range(i + 1, len(claims)):
            a, b = claims[i], claims[j]
            ad, aa, adt, ak = _claim_features(a["text"])
            bd, ba, bdt, bk = _claim_features(b["text"])
            shared_subject = (ad & bd) or (adt & bdt) or (ak & bk)
            if not shared_subject:
                continue
            same_party = a["party_id"] is not None and a["party_id"] == b["party_id"]
            if aa and ba and not (aa & ba):
                kind = "AMOUNT" if same_party else "CROSS_PARTY"
                add(kind, "Different amounts stated for the same subject", a, b, [],
                    f"{a['claim_ref']} ({a['party_name'] or 'party'}) states {_fmt_amounts(aa)}; "
                    f"{b['claim_ref']} ({b['party_name'] or 'party'}) states {_fmt_amounts(ba)}. "
                    "The amounts stated for the same subject do not match.",
                    "ASSERTED")
            elif adt and bdt and not (adt & bdt):
                add("TEMPORAL", "Different dates stated for the same subject", a, b, [],
                    f"{a['claim_ref']} refers to {', '.join(sorted(adt))}; {b['claim_ref']} refers to "
                    f"{', '.join(sorted(bdt))}. The stated dates for the same subject differ.",
                    "ASSERTED")

    # 3. significant claims without supporting evidence
    linked = {r["claim_id"] for r in conn.execute("SELECT DISTINCT claim_id FROM evidence_references WHERE case_id=?", (case_id,))}
    for c in claims:
        _, amounts, dates, _ = _claim_features(c["text"])
        significant = bool(amounts or dates)
        if significant and c["id"] not in linked:
            add("MISSING_SUPPORT", "A significant claim lacks supporting evidence", c, None, [],
                f"{c['claim_ref']} makes a specific factual claim ({_fmt_amounts(amounts) if amounts else ', '.join(sorted(dates))}) "
                "but no uploaded evidence has been linked to it. Support may exist outside the material supplied.",
                "ASSERTED")

    created = 0
    for f in found:
        ref = next_ref(conn, case_id, "contradiction", "C")
        conn.execute(
            "INSERT INTO contradictions(case_id, contradiction_ref, kind, title, claim_a_id, claim_b_id, evidence_ids,"
            " explanation, confidence, origin, verification_status, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, ref, f["kind"], f["title"], f["a"]["id"] if f["a"] else None, f["b"]["id"] if f["b"] else None,
             json.dumps(f["evidence"]), f["explanation"], f["basis"], f["origin"], "REQUIRES_HUMAN_REVIEW", None))
        created += 1
    return {"contradictions": created}


def _fmt_amounts(amounts) -> str:
    return ", ".join(f"₹{a:,.0f}" for a in sorted(amounts)) if amounts else "an unspecified amount"
