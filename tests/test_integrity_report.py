"""Phase 6: human decision, report export and integrity verification."""
from conftest import auth, login, wait_analysis

from test_intelligence import _seed


def _analysed(client, token):
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    return cid


def test_decision_requires_chair_and_is_recorded(client):
    officer = login(client)
    cid = _analysed(client, officer)
    body = {"status": "PRELIMINARY_RESOLUTION_ACCEPTED", "decision": "Deposit to be returned less agreed deduction.",
            "reason": "The payment record supports the amount received; the deduction requires agreement.",
            "evidence_ids": ["E-001", "E-002"], "legal_refs": ["IN-TPA-1882-S108"], "observations": "Both parties heard."}
    assert client.post(f"/api/cases/{cid}/decision", headers=auth(officer), json=body).status_code == 403
    chair = login(client, "chair")
    r = client.post(f"/api/cases/{cid}/decision", headers=auth(chair), json=body)
    assert r.status_code == 201, r.text
    assert r.json()["decision_ref"].startswith("D-") and r.json()["human_validated"] == 1
    # a case cannot have two decisions
    assert client.post(f"/api/cases/{cid}/decision", headers=auth(chair), json=body).status_code == 409
    case = client.get(f"/api/cases/{cid}", headers=auth(chair)).json()
    assert case["status"] == "RESOLVED" and case["current_stage"] == "CLOSED"


def test_decision_requiring_more_evidence_keeps_case_open(client):
    officer = login(client)
    cid = _analysed(client, officer)
    chair = login(client, "chair")
    r = client.post(f"/api/cases/{cid}/decision", headers=auth(chair), json={
        "status": "ADDITIONAL_EVIDENCE_REQUIRED", "decision": "More evidence needed", "reason": "Invoice not provided."})
    assert r.status_code == 201
    assert client.get(f"/api/cases/{cid}", headers=auth(chair)).json()["status"] == "EVIDENCE_REQUESTED"


def test_report_json_has_all_sections_and_labels(client):
    officer = login(client)
    cid = _analysed(client, officer)
    rep = client.get(f"/api/cases/{cid}/report.json", headers=auth(officer)).json()
    for i in range(1, 13):
        assert any(k.startswith(f"{i}_") for k in rep), f"section {i} missing"
    assert rep["4_evidence"] and all(e["sha256"] for e in rep["4_evidence"])
    assert rep["9_ai_assisted_analysis"]["findings"]
    assert rep["12_audit_information"]["audit_chain"]["ok"] is True
    assert rep["disclaimer"]


def test_report_pdf_generates(client):
    officer = login(client)
    cid = _analysed(client, officer)
    r = client.get(f"/api/cases/{cid}/report.pdf", headers=auth(officer))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-" and len(r.content) > 3000


def test_integrity_verifies_then_warns_on_tamper(client):
    officer = login(client)
    cid = _analysed(client, officer)
    v = client.get(f"/api/cases/{cid}/integrity", headers=auth(officer)).json()
    assert v["status"] == "VERIFIED" and v["audit_chain"]["ok"] and v["integrity_chain"]["ok"]
    assert v["anchor"]["status"] in ("LOCAL_ONLY", "NOT_PUBLISHED")

    from app.db import db
    with db() as c:
        path = c.execute("SELECT stored_path FROM evidence WHERE case_id=? ORDER BY id LIMIT 1", (cid,)).fetchone()[0]
    with open(path, "ab") as f:
        f.write(b"tampered\n")
    v2 = client.get(f"/api/cases/{cid}/integrity", headers=auth(officer)).json()
    assert v2["status"] == "WARNING" and v2["evidence"]["mismatch"]


def test_report_and_integrity_are_access_scoped(client):
    officer = login(client)
    cid = _analysed(client, officer)
    respondent = login(client, "respondent")
    assert client.get(f"/api/cases/{cid}/report.json", headers=auth(respondent)).status_code == 404
    assert client.get(f"/api/cases/{cid}/integrity", headers=auth(respondent)).status_code == 404
