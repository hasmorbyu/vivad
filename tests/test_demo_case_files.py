"""The committed demo_case/ folder, uploaded and analysed, reproduces the demonstration results."""
from pathlib import Path

from conftest import auth, login, wait_analysis, wait_evidence

DEMO = Path(__file__).resolve().parents[1] / "demo_case"
EVIDENCE = [p for p in sorted(DEMO.iterdir()) if p.suffix.lower() in (".txt", ".csv", ".eml") and p.name != "README.txt"]

COMPLAINANT_CLAIM = "The full Rs. 40,000 security deposit was paid on 14 Sep 2026."
RESPONDENT_CLAIM = "Only Rs. 25,000 was paid towards the deposit and Rs. 15,000 is deductible for damage."


def test_demo_case_folder_reproduces_results(client):
    assert len(EVIDENCE) == 6, [p.name for p in EVIDENCE]
    token = login(client)
    cid = client.post("/api/cases", headers=auth(token), json={
        "title": "Security deposit deduction dispute", "category": "RENTAL_DISPUTE", "amount": 40000,
        "location": "Bengaluru"}).json()["id"]
    a = client.post(f"/api/cases/{cid}/parties", headers=auth(token), json={"name": "Aarav Menon", "role": "COMPLAINANT"}).json()
    b = client.post(f"/api/cases/{cid}/parties", headers=auth(token), json={"name": "Neel Kapoor", "role": "RESPONDENT"}).json()
    client.post(f"/api/cases/{cid}/statements", headers=auth(token), json={"party_id": a["id"], "claim": COMPLAINANT_CLAIM, "when_text": "14 Sep 2026"})
    client.post(f"/api/cases/{cid}/statements", headers=auth(token), json={"party_id": b["id"], "claim": RESPONDENT_CLAIM})

    for p in EVIDENCE:
        r = client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": (p.name, p.read_bytes())})
        assert r.status_code == 202, (p.name, r.text)
    files = wait_evidence(client, token, cid)
    assert len(files) == 6 and all(f["status"] == "PARSED" for f in files)
    assert {f["evidence_ref"] for f in files} == {f"E-00{i}" for i in range(1, 7)}

    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    status = wait_analysis(client, token, cid)
    assert status["state"] == "DONE", status

    claims = client.get(f"/api/cases/{cid}/claims", headers=auth(token)).json()
    assert len(claims) == 2
    assert any(c["amount"] == 40000.0 and c["status"] == "SUPPORTED" for c in claims)
    assert any(c["amount"] == 25000.0 and c["status"] == "UNSUPPORTED" for c in claims)

    contradictions = client.get(f"/api/cases/{cid}/contradictions", headers=auth(token)).json()
    kinds = {c["kind"] for c in contradictions}
    assert "CROSS_PARTY" in kinds and "MISSING_SUPPORT" in kinds

    legal = client.get(f"/api/cases/{cid}/legal", headers=auth(token)).json()
    assert legal and any("Transfer of Property Act" in r["act"] for r in legal)

    graph = client.get(f"/api/cases/{cid}/graph", headers=auth(token)).json()
    kinds = {n["data"]["kind"] for n in graph["nodes"]}
    assert {"party", "claim", "evidence", "contradiction", "law"} <= kinds
