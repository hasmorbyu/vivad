"""AI-assisted case analysis with schema validation and a deterministic fallback.

The model is given a bounded, structured digest of the case. Its output is validated
against a schema, evidence IDs are checked against the case, and unknown IDs or empty items
are dropped. If no provider is configured, or the call fails, a deterministic analysis built
from the same structured data is used instead. AI never creates claims, contradictions or
decisions; it only summarises and suggests.
"""
import json

from .provider import SYSTEM_PROMPT, AIUnavailable, AIProvider, get_provider
from .schemas import AnalysisOut

PROMPT_VERSION = "vivad-analysis-v1"


def build_payload(case: dict, parties: list, statements: list, evidence: list, claims: list, contradictions: list) -> dict:
    return {
        "case": {
            "id": case.get("id"), "category": case.get("category"), "title": case.get("title"),
            "description": case.get("description"), "amount": case.get("amount"),
            "currency": case.get("currency", "INR"), "requested_resolution": case.get("requested_resolution"),
        },
        "parties": [{"name": p.get("name"), "role": p.get("role")} for p in parties],
        "statements": [{"party": s.get("party_name"), "kind": s.get("kind"),
                        "claim": s.get("claim") or s.get("what")} for s in statements],
        "evidence": [{"id": e.get("evidence_ref"), "filename": e.get("filename"), "type": e.get("source_type"),
                      "amounts": e.get("amounts", []), "dates": e.get("dates", []),
                      "documents": e.get("documents", [])} for e in evidence],
        "deterministic_claims": [{"id": c.get("claim_ref"), "party": c.get("party_name"), "text": c.get("text"),
                                  "amount": c.get("amount"), "date": c.get("date"), "status": c.get("status"),
                                  "evidence": c.get("evidence_refs", [])} for c in claims],
        "deterministic_contradiction_candidates": [{"id": x.get("contradiction_ref"), "kind": x.get("kind"),
                                                    "title": x.get("title"), "explanation": x.get("explanation")} for x in contradictions],
        "instructions": (
            "Return JSON with keys: summary (string), facts_supported (list of {text, evidence_ids, basis}), "
            "claims_requiring_verification (list of {text, reason}), potential_contradictions "
            "(list of {kind, title, evidence_ids, explanation, basis}), missing_information (list of {text, reason}), "
            "possible_resolution_paths (list of {text, evidence_ids, basis}), hearing_questions (list of strings). "
            "Every evidence_id must be one of the supplied evidence IDs. Reference findings only to supplied data."
        ),
    }


def analyze(case: dict, parties: list, statements: list, evidence: list, claims: list, contradictions: list,
            provider: AIProvider | None = None) -> dict:
    payload = build_payload(case, parties, statements, evidence, claims, contradictions)
    valid_ids = {e.get("evidence_ref") for e in evidence if e.get("evidence_ref")}
    prov = provider or get_provider()
    if not prov.configured():
        return {"ai_available": False, "reason": f"{prov.name.upper()}_API_KEY not set",
                "provider": prov.name, "prompt_version": PROMPT_VERSION,
                "analysis": deterministic_analysis(payload), "validation": "DETERMINISTIC",
                "input": payload}
    try:
        raw = prov.generate_json(SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False, default=str))
    except AIUnavailable as e:
        return {"ai_available": False, "reason": str(e), "provider": prov.name, "prompt_version": PROMPT_VERSION,
                "analysis": deterministic_analysis(payload), "validation": f"AI UNAVAILABLE: {e}", "input": payload}
    from .schemas import validate_analysis
    result = validate_analysis(raw, valid_ids)
    if not result.ok or not result.data:
        return {"ai_available": False, "reason": "schema validation failed", "provider": prov.name,
                "prompt_version": PROMPT_VERSION, "analysis": deterministic_analysis(payload),
                "validation": "REJECTED: " + "; ".join(result.errors), "raw": raw, "input": payload}
    return {"ai_available": True, "provider": prov.name, "prompt_version": PROMPT_VERSION,
            "analysis": result.data.model_dump(), "validation": "SCHEMA OK" + ("; " + "; ".join(result.errors) if result.errors else ""),
            "dropped_evidence_ids": result.dropped_evidence_ids, "input": payload}


def _amt(a) -> str:
    return f"₹{a:,.0f}" if a is not None else "an amount"


def deterministic_analysis(payload: dict) -> dict:
    """Build the same section structure from deterministic data, with no model involved."""
    case = payload["case"]
    claims = payload["deterministic_claims"]
    contradictions = payload["deterministic_contradiction_candidates"]
    evidence = payload["evidence"]
    parties = payload["parties"]

    supported = [c for c in claims if c["status"] == "SUPPORTED"]
    unresolved = [c for c in claims if c["status"] in ("REQUIRES_HUMAN_REVIEW", "UNSUPPORTED", "PARTIALLY_SUPPORTED")]

    facts = [{"text": f"{c['party'] or 'A party'} claims: {c['text']}", "evidence_ids": c["evidence"], "basis": c["status"]}
             for c in supported]
    verify = [{"text": c["text"], "reason": f"Claim {c['id']} is {c['status'].replace('_', ' ').lower()} on the material supplied."}
              for c in unresolved]
    contr = [{"kind": x["kind"], "title": x["title"], "evidence_ids": [], "explanation": x["explanation"], "basis": "DETERMINISTIC"} for x in contradictions]
    missing = [{"text": "No evidence has been linked to this claim.", "reason": x["explanation"]} for x in contradictions if x["kind"] == "MISSING_SUPPORT"]
    unparsed = [e for e in evidence if not (e.get("amounts") or e.get("dates") or e.get("documents"))]
    if unparsed:
        missing.append({"text": f"{len(unparsed)} evidence item(s) yielded no machine-readable facts.",
                        "reason": "These may be images, transcripts or scanned documents and require human reading."})
    paths = []
    if contradictions:
        paths.append({"text": "Request clarification from the parties on the points where the material does not agree.",
                      "evidence_ids": [], "basis": f"{len(contradictions)} potential inconsistency(ies) were identified."})
    if missing:
        paths.append({"text": "Request additional evidence for the claims that are not currently supported.",
                      "evidence_ids": [], "basis": "Some specific claims have no linked evidence."})
    paths.append({"text": "Continue human review; consider mediation or conciliation where both parties seek a settlement.",
                  "evidence_ids": [], "basis": "VIVAD issues no decision; a human makes any resolution."})
    questions = [
        "Can each party confirm the amount and date in dispute, and identify the document that supports it?",
        "Is there a written agreement, receipt or record that both parties accept as authentic?",
        "What outcome would each party consider acceptable, and is settlement possible?",
    ]
    party_names = ", ".join(p["name"] for p in parties if p.get("name")) or "the parties"
    summary = (
        f"This dispute ({case.get('category') or 'uncategorised'}) involves {party_names}. "
        f"{len(claims)} structured claim(s) were extracted and {len(evidence)} evidence item(s) were considered. "
        f"{len(supported)} claim(s) currently have documentary support and {len(unresolved)} await verification. "
        f"{len(contradictions)} potential inconsistency(ies) were flagged for human review. "
        "VIVAD does not decide the dispute; this summary assists an authorised human reviewer."
    )
    return AnalysisOut(summary=summary, facts_supported=facts[:40], claims_requiring_verification=verify[:40],
                       potential_contradictions=contr[:40], missing_information=missing[:20],
                       possible_resolution_paths=paths, hearing_questions=questions).model_dump()
