"""Analysis orchestration.

Runs in a background thread with a pollable per-step status. The order is fixed:
integrity -> deterministic extraction -> claims -> evidence links -> timeline ->
contradictions -> legal association -> AI-assisted analysis -> findings. AI is optional and
grounded; deterministic stages always run, so the workflow degrades rather than fails.
"""
import json
import threading
import time
from datetime import datetime, timezone

from . import audit
from .ai import service as ai
from .db import db
from .ingest import recompute_extraction, verify_evidence_integrity
from .intel import claims as claims_mod
from .intel import contradictions as contradictions_mod
from .intel import legal as legal_mod
from .intel import timeline as timeline_mod
from .ledger import now_iso
from .services import case_row, parse_json

STATUS: dict[str, dict] = {}
LOCK = threading.Lock()

STEPS = [
    "VERIFYING EVIDENCE INTEGRITY",
    "EXTRACTING ENTITIES FROM EVIDENCE",
    "EXTRACTING CLAIMS FROM STATEMENTS",
    "LINKING EVIDENCE TO CLAIMS",
    "BUILDING TIMELINE",
    "DETECTING POTENTIAL CONTRADICTIONS",
    "ASSOCIATING LEGAL REFERENCES",
    "AI-ASSISTED CASE ANALYSIS",
    "GENERATING FINDINGS",
]


def get_status(case_id: str) -> dict:
    with LOCK:
        s = STATUS.get(case_id)
    if s:
        return s
    with db() as c:
        row = c.execute("SELECT analysis_state, analysis_at, analysis_json FROM cases WHERE id=?", (case_id,)).fetchone()
    if row and row["analysis_json"]:
        return json.loads(row["analysis_json"])
    return {"state": row["analysis_state"] if row else "NOT_RUN",
            "steps": [{"name": n, "status": "WAITING", "detail": ""} for n in STEPS]}


def start_analysis(case_id: str, user: dict | None = None) -> bool:
    with LOCK:
        cur = STATUS.get(case_id)
        if cur and cur["state"] == "RUNNING":
            return False
        STATUS[case_id] = {"state": "RUNNING", "started": time.time(),
                           "steps": [{"name": n, "status": "WAITING", "detail": ""} for n in STEPS]}
    threading.Thread(target=_run, args=(case_id, user), daemon=True).start()
    return True


def _set(case_id, i, status, detail=""):
    with LOCK:
        STATUS[case_id]["steps"][i].update(status=status, detail=detail)


def _run(case_id: str, user: dict | None) -> None:
    i = 0
    try:
        with db() as c:
            case = case_row(c, case_id)
            if not case:
                raise RuntimeError("case not found")

            i = 0
            _set(case_id, i, "PROCESSING")
            integ = verify_evidence_integrity(c, case_id)
            _set(case_id, i, "OK" if not integ["mismatch"] else "WARN",
                 f"{integ['verified']}/{integ['total']} verified" + (f"; mismatch {', '.join(integ['mismatch'])}" if integ["mismatch"] else ""))
            c.commit()

            i = 1
            _set(case_id, i, "PROCESSING")
            n = recompute_extraction(c, case_id)
            _set(case_id, i, "OK", f"facts re-derived for {n} evidence item(s)")
            c.commit()

            i = 2
            _set(case_id, i, "PROCESSING")
            claim_res = claims_mod.extract_claims(c, case_id)
            _set(case_id, i, "OK", f"{claim_res['claims']} claim(s) extracted")
            i = 3
            _set(case_id, i, "OK", f"{claim_res['evidence_links']} evidence link(s)")
            c.commit()

            i = 4
            _set(case_id, i, "PROCESSING")
            tl = timeline_mod.build_timeline(c, case_id)
            _set(case_id, i, "OK", f"{tl['events']} event(s)")
            c.commit()

            i = 5
            _set(case_id, i, "PROCESSING")
            contra = contradictions_mod.detect_contradictions(c, case_id)
            _set(case_id, i, "OK", f"{contra['contradictions']} potential contradiction(s)")
            c.commit()

            i = 6
            _set(case_id, i, "PROCESSING")
            loaded = legal_mod.load_dataset(c)
            associated = legal_mod.associate(c, case_id)
            _set(case_id, i, "OK" if loaded else "WARN", f"{associated} reference(s) associated" + ("" if loaded else "; no legal dataset found"))
            c.commit()

            i = 7
            _set(case_id, i, "PROCESSING")
            bundle = _gather(c, case_id)
            result = ai.analyze(case, bundle["parties"], bundle["statements"], bundle["evidence"],
                                bundle["claims"], bundle["contradictions"])
            analysis_id = c.execute(
                "INSERT INTO ai_analyses(case_id, provider, model, prompt_version, status, input_json, output_json, validation, created_at)"
                " VALUES(?,?,?,?,?,?,?,?,?)",
                (case_id, result.get("provider"), None, result.get("prompt_version"),
                 "OK" if result.get("ai_available") else "FALLBACK",
                 json.dumps(result.get("input"), default=str), json.dumps(result.get("analysis"), default=str),
                 result.get("validation"), now_iso())).lastrowid
            _set(case_id, i, "OK" if result.get("ai_available") else "UNAVAILABLE",
                 (f"AI {result.get('provider')} analysis validated" if result.get("ai_available")
                  else f"AI UNAVAILABLE ({result.get('reason')}); deterministic analysis used"))
            c.commit()

            i = 8
            _set(case_id, i, "PROCESSING")
            nf = _store_findings(c, case_id, analysis_id, result, bundle)
            summary = (result.get("analysis") or {}).get("summary", "")
            source = f"AI:{result.get('provider')}" if result.get("ai_available") else "DETERMINISTIC"
            c.execute("UPDATE cases SET summary_text=?, summary_source=?, summary_at=?, status='AWAITING_REVIEW',"
                      " current_stage='HUMAN_REVIEW', next_action='Human review of AI findings', updated_at=? WHERE id=?",
                      (summary, source, now_iso(), now_iso(), case_id))
            audit.record(c, user, "AI_ANALYSIS_GENERATED", case_id=case_id, object_type="case", object_id=case_id,
                         new_state="AWAITING_REVIEW", detail=f"{nf} finding(s); source={source}")
            _set(case_id, i, "OK", f"{nf} finding(s) ready for human review")
            c.commit()

        with LOCK:
            STATUS[case_id].update(state="DONE", finished=time.time(), summary={"findings": nf})
            snap = dict(STATUS[case_id])
        with db() as c:
            c.execute("UPDATE cases SET analysis_state='DONE', analysis_at=?, analysis_json=? WHERE id=?",
                      (now_iso(), json.dumps(snap, default=str), case_id))
    except Exception as e:  # noqa: BLE001
        _set(case_id, i, "ERROR", f"{type(e).__name__}: {e}")
        with LOCK:
            STATUS[case_id].update(state="ERROR", error=str(e))
            snap = dict(STATUS[case_id])
        try:
            with db() as c:
                c.execute("UPDATE cases SET analysis_state='ERROR', analysis_json=? WHERE id=?", (json.dumps(snap, default=str), case_id))
        except Exception:  # noqa: BLE001
            pass


def _gather(conn, case_id: str) -> dict:
    parties = [dict(r) for r in conn.execute("SELECT * FROM parties WHERE case_id=?", (case_id,))]
    statements = [dict(r) for r in conn.execute(
        "SELECT s.*, p.name party_name FROM statements s LEFT JOIN parties p ON p.id=s.party_id WHERE s.case_id=? ORDER BY s.id", (case_id,))]
    claims = []
    for r in conn.execute(
        "SELECT c.*, p.name party_name FROM claims c LEFT JOIN parties p ON p.id=c.party_id WHERE c.case_id=? ORDER BY c.id", (case_id,)):
        d = dict(r)
        d["evidence_refs"] = [x[0] for x in conn.execute(
            "SELECT ev.evidence_ref FROM evidence_references er JOIN evidence ev ON ev.id=er.evidence_id WHERE er.claim_id=?", (d["id"],))]
        claims.append(d)
    contradictions = [dict(r) for r in conn.execute("SELECT * FROM contradictions WHERE case_id=? ORDER BY id", (case_id,))]
    evidence = []
    for r in conn.execute("SELECT id, evidence_ref, filename, source_type, extracted_json FROM evidence WHERE case_id=? ORDER BY id", (case_id,)):
        data = parse_json(r["extracted_json"], {})
        evidence.append({
            "id": r["id"], "evidence_ref": r["evidence_ref"], "filename": r["filename"], "source_type": r["source_type"],
            "amounts": data.get("amounts", [])[:20],
            "dates": [x.get("iso") for x in data.get("dates", [])][:20],
            "documents": [e.get("value") for e in data.get("entities", []) if e.get("type") == "DOCUMENT_ID"][:20],
        })
    return {"parties": parties, "statements": statements, "claims": claims,
            "contradictions": contradictions, "evidence": evidence}


def _store_findings(conn, case_id, analysis_id, result, bundle) -> int:
    conn.execute("DELETE FROM ai_findings WHERE case_id=?", (case_id,))
    a = result.get("analysis") or {}
    origin = "AI" if result.get("ai_available") else "DETERMINISTIC"
    seq = 0

    def add(kind, title, body, evidence_ids, validation, confidence="", claim_ids=None):
        nonlocal seq
        seq += 1
        conn.execute(
            "INSERT INTO ai_findings(case_id, finding_ref, analysis_id, kind, title, body, evidence_ids, claim_ids,"
            " confidence, validation, origin, human_status, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (case_id, f"F-{seq:03d}", analysis_id, kind, title, body,
             json.dumps(list(dict.fromkeys(evidence_ids))), json.dumps(claim_ids or []), confidence, validation,
             origin, "PENDING", now_iso()))

    for f in a.get("facts_supported", []):
        add("FACT_SUPPORTED", "Fact supported by evidence", f.get("text", ""), f.get("evidence_ids", []),
            f.get("basis") or result.get("validation"))
    for f in a.get("claims_requiring_verification", []):
        add("CLAIM_REQUIRING_VERIFICATION", "Claim requiring verification", f.get("text", ""), [], f.get("reason"))
    for f in a.get("potential_contradictions", []):
        add("CONTRADICTION", f.get("title") or "Potential contradiction", f.get("explanation", ""),
            f.get("evidence_ids", []), f.get("basis") or result.get("validation"))
    for f in a.get("missing_information", []):
        add("MISSING_INFORMATION", "Missing information", f.get("text", ""), [], f.get("reason"))
    for f in a.get("possible_resolution_paths", []):
        add("RESOLUTION_PATH", "Possible next step", f.get("text", ""), f.get("evidence_ids", []), f.get("basis"))
    for q in a.get("hearing_questions", []):
        add("HEARING_QUESTION", "Question for the hearing", q, [], None)
    # deterministic contradictions are always represented, whatever the AI produced
    for x in bundle["contradictions"]:
        ev_refs = _refs_for_contradiction(conn, case_id, x["id"])
        add("CONTRADICTION", x["title"] or "Potential contradiction", x["explanation"], ev_refs, None, x["confidence"])
    return seq


def _refs_for_contradiction(conn, case_id, contradiction_id) -> list[str]:
    row = conn.execute("SELECT evidence_ids FROM contradictions WHERE id=?", (contradiction_id,)).fetchone()
    ids = parse_json(row["evidence_ids"] if row else None, [])
    refs = []
    for eid in ids:
        e = conn.execute("SELECT evidence_ref FROM evidence WHERE id=?", (eid,)).fetchone()
        if e:
            refs.append(e["evidence_ref"])
    return refs
