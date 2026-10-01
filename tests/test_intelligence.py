"""Phase 3: claims, evidence links, timeline, contradictions, legal association, AI fallback."""
from conftest import auth, login, wait_analysis, wait_evidence

AGREEMENT = (
    "RENTAL AGREEMENT NO. RA-2026-0042\n"
    "Landlord: Neel Kapoor\nTenant: Aarav Menon\n"
    "Monthly rent: Rs. 20,000\n"
    "Security deposit: Rs. 40,000 paid on 2026-09-14\n"
    "Property: 12 Rose Apartments, Bengaluru\n"
)
PAYMENTS = (
    "payment_id,payment_date,payer,payee,amount,status,reference\n"
    "P-1001,2026-09-14,Aarav Menon,Neel Kapoor,40000,SUCCESS,UPI/RA-2026-0042/626214321877\n"
)


def _seed(client, token):
    cid = client.post("/api/cases", headers=auth(token),
                      json={"title": "Security deposit dispute", "category": "RENTAL_DISPUTE", "amount": 40000}).json()["id"]
    a = client.post(f"/api/cases/{cid}/parties", headers=auth(token), json={"name": "Aarav Menon", "role": "COMPLAINANT"}).json()
    b = client.post(f"/api/cases/{cid}/parties", headers=auth(token), json={"name": "Neel Kapoor", "role": "RESPONDENT"}).json()
    client.post(f"/api/cases/{cid}/statements", headers=auth(token), json={
        "party_id": a["id"], "claim": "The full Rs. 40,000 security deposit was paid on 14 Sep 2026."})
    client.post(f"/api/cases/{cid}/statements", headers=auth(token), json={
        "party_id": b["id"], "claim": "Only Rs. 25,000 was paid towards the deposit and Rs. 15,000 is deductible for damage."})
    client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("agreement.txt", AGREEMENT.encode())})
    client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("payments.csv", PAYMENTS.encode())})
    wait_evidence(client, token, cid)
    return cid, a, b


def test_full_interrogation_pipeline(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    assert client.post(f"/api/cases/{cid}/analyze", headers=auth(token)).status_code == 202
    status = wait_analysis(client, token, cid)
    assert status["state"] == "DONE", status
    steps = {s["name"]: s for s in status["steps"]}
    assert steps["VERIFYING EVIDENCE INTEGRITY"]["status"] == "OK"
    assert steps["AI-ASSISTED CASE ANALYSIS"]["status"] in ("OK", "UNAVAILABLE")

    claims = client.get(f"/api/cases/{cid}/claims", headers=auth(token)).json()
    assert len(claims) == 2
    comp = next(c for c in claims if c["party_name"] == "Aarav Menon")
    resp = next(c for c in claims if c["party_name"] == "Neel Kapoor")
    assert comp["amount"] == 40000.0 and comp["status"] == "SUPPORTED"
    assert any(e["evidence_ref"] == "E-001" for e in comp["evidence"]) or any(e["evidence_ref"] == "E-002" for e in comp["evidence"])
    assert resp["amount"] == 25000.0 and resp["status"] == "UNSUPPORTED"


def test_timeline_is_evidence_linked(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    timeline = client.get(f"/api/cases/{cid}/timeline", headers=auth(token)).json()
    assert len(timeline) > 0
    times = [t["event_time"] for t in timeline]
    assert times == sorted(times)
    evidence_events = [t for t in timeline if t["evidence_ref"]]
    assert evidence_events and all(t["event_ref"] for t in timeline)


def test_contradictions_are_detected_and_reviewable(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    rows = client.get(f"/api/cases/{cid}/contradictions", headers=auth(token)).json()
    assert rows, "expected at least one potential contradiction"
    kinds = {r["kind"] for r in rows}
    assert "CROSS_PARTY" in kinds or "AMOUNT" in kinds
    assert all(r["verification_status"] == "REQUIRES_HUMAN_REVIEW" for r in rows)
    ref = rows[0]["contradiction_ref"]
    r = client.patch(f"/api/cases/{cid}/contradictions/{ref}", headers=auth(token),
                     json={"verification_status": "CONFIRMED_INCONSISTENCY", "note": "reviewed"})
    assert r.status_code == 200 and r.json()["verification_status"] == "CONFIRMED_INCONSISTENCY"


def test_legal_references_associated_with_sources(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    refs = client.get(f"/api/cases/{cid}/legal", headers=auth(token)).json()
    assert refs, "expected legal references for a rental deposit dispute"
    assert all(r["source_url"].startswith("http") for r in refs)
    assert all(r["disclaimer"] for r in refs)
    assert any("Transfer of Property Act" in r["act"] for r in refs)


def test_ai_analysis_structure_and_case_status(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    analysis = client.get(f"/api/cases/{cid}/analysis", headers=auth(token)).json()
    assert analysis["status"] == "FALLBACK" and analysis["provider"] in ("gemini", "groq")
    out = analysis["analysis"]
    for key in ("summary", "facts_supported", "claims_requiring_verification", "potential_contradictions",
                "missing_information", "possible_resolution_paths", "hearing_questions"):
        assert key in out
    assert analysis["findings"] and analysis["awaiting_review"] == len(analysis["findings"])
    case = client.get(f"/api/cases/{cid}", headers=auth(token)).json()
    assert case["status"] == "AWAITING_REVIEW" and case["current_stage"] == "HUMAN_REVIEW"
    assert case["summary_source"] == "DETERMINISTIC"


def test_analysis_requires_access(client):
    officer = login(client)
    cid, _, _ = _seed(client, officer)
    respondent = login(client, "respondent")
    assert client.post(f"/api/cases/{cid}/analyze", headers=auth(respondent)).status_code == 404
    assert client.get(f"/api/cases/{cid}/claims", headers=auth(respondent)).status_code == 404
