"""Phase 2: parties, statements and evidence intake."""
import hashlib

from conftest import auth, login, wait_evidence

AGREEMENT = (
    "RENTAL AGREEMENT NO. RA-2026-0042\n"
    "Landlord: Neel Kapoor\n"
    "Tenant: Aarav Menon\n"
    "Monthly rent: Rs. 20,000\n"
    "Security deposit: Rs. 40,000 paid on 2026-09-14\n"
    "Property: 12 Rose Apartments, Bengaluru\n"
)

PAYMENT_CSV = (
    "payment_id,payment_date,payer,payee,amount,status,reference\n"
    "P-1001,2026-09-14,Aarav Menon,Neel Kapoor,40000,SUCCESS,UPI/RA-2026-0042/626214321877\n"
    "P-1002,2026-09-20,Aarav Menon,Neel Kapoor,5000,SUCCESS,UPI/RA-2026-0042/626214321999\n"
)


def _case(client, token, title="Deposit dispute"):
    r = client.post("/api/cases", headers=auth(token), json={"title": title, "category": "RENTAL_DISPUTE", "amount": 40000})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_add_parties_advances_stage(client):
    token = login(client)
    cid = _case(client, token)
    assert client.post(f"/api/cases/{cid}/parties", headers=auth(token),
                       json={"name": "Aarav Menon", "role": "COMPLAINANT", "contact": "+91 98765 43210"}).status_code == 201
    r = client.post(f"/api/cases/{cid}/parties", headers=auth(token),
                    json={"name": "Neel Kapoor", "role": "RESPONDENT"})
    assert r.status_code == 201
    parties = client.get(f"/api/cases/{cid}/parties", headers=auth(token)).json()
    assert {p["name"] for p in parties} == {"Aarav Menon", "Neel Kapoor"}
    case = client.get(f"/api/cases/{cid}", headers=auth(token)).json()
    assert case["status"] == "PROCESSING" and case["current_stage"] == "EVIDENCE"
    assert case["party_summary"] == "Aarav Menon vs Neel Kapoor"


def test_statement_records_and_audits(client):
    token = login(client)
    cid = _case(client, token)
    p = client.post(f"/api/cases/{cid}/parties", headers=auth(token), json={"name": "Aarav Menon", "role": "COMPLAINANT"}).json()
    r = client.post(f"/api/cases/{cid}/statements", headers=auth(token), json={
        "party_id": p["id"], "what": "Paid the deposit", "when_text": "2026-09-14",
        "claim": "The full Rs. 40,000 security deposit was paid.", "desired_resolution": "Return the deposit."})
    assert r.status_code == 201
    rows = client.get(f"/api/cases/{cid}/statements", headers=auth(token)).json()
    assert len(rows) == 1 and rows[0]["claim"].startswith("The full")
    assert rows[0]["party_name"] == "Aarav Menon" and rows[0]["submitted_by"] is not None


def test_rejects_party_from_other_case(client):
    token = login(client)
    cid, other = _case(client, token), _case(client, token, "Other")
    p = client.post(f"/api/cases/{other}/parties", headers=auth(token), json={"name": "X", "role": "COMPLAINANT"}).json()
    r = client.post(f"/api/cases/{cid}/statements", headers=auth(token), json={"party_id": p["id"], "claim": "x"})
    assert r.status_code == 422


def test_evidence_upload_hashes_parses_and_issues_e_refs(client):
    token = login(client)
    cid = _case(client, token)
    first = client.post(f"/api/cases/{cid}/evidence", headers=auth(token),
                        files={"file": ("agreement.txt", AGREEMENT.encode())})
    assert first.status_code == 202 and first.json()["evidence_ref"] == "E-001"
    assert first.json()["sha256"] == hashlib.sha256(AGREEMENT.encode()).hexdigest()
    second = client.post(f"/api/cases/{cid}/evidence", headers=auth(token),
                         files={"file": ("payments.csv", PAYMENT_CSV.encode())})
    assert second.json()["evidence_ref"] == "E-002"
    files = wait_evidence(client, token, cid)
    assert {f["status"] for f in files} == {"PARSED"}
    by_ref = {f["evidence_ref"]: f for f in files}
    assert by_ref["E-001"]["source_type"] == "DOCUMENT" and by_ref["E-001"]["record_count"] >= 6
    assert by_ref["E-002"]["source_type"] == "SPREADSHEET" and by_ref["E-002"]["record_count"] == 2


def test_evidence_upload_errors(client):
    token = login(client)
    cid = _case(client, token)
    ok = b"payment_id,amount\n1,10\n"
    assert client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("a.csv", ok)}).status_code == 202
    assert client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("copy.csv", ok)}).status_code == 409
    assert client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("x.exe", b"MZ")}).status_code == 415
    assert client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("e.txt", b"")}).status_code == 400
    r = client.post(f"/api/cases/{cid}/evidence", headers=auth(token), files={"file": ("../../evil.txt", b"hi\n")})
    assert r.status_code == 202 and "/" not in r.json()["filename"] and ".." not in r.json()["filename"]
    wait_evidence(client, token, cid)  # let background parsing finish before the temp dir is removed


def test_evidence_detail_and_facts(client):
    token = login(client)
    cid = _case(client, token)
    eid = client.post(f"/api/cases/{cid}/evidence", headers=auth(token),
                      files={"file": ("agreement.txt", AGREEMENT.encode())}).json()["id"]
    wait_evidence(client, token, cid)
    d = client.get(f"/api/cases/{cid}/evidence/{eid}", headers=auth(token)).json()
    assert d["evidence_ref"] == "E-001" and d["status"] == "PARSED"
    assert "40,000" in d["extracted"]["entities"][0]["value"] or 40000.0 in d["extracted"]["amounts"]
    assert any("2026-09-14" in dt["iso"] for dt in d["extracted"]["dates"])
    assert d["integrity"] and d["integrity"][0]["object_hash"] == d["sha256"]
    assert any(h["action"] == "EVIDENCE_UPLOADED" for h in d["audit_history"])


def test_evidence_reader_lines_and_verify(client):
    token = login(client)
    cid = _case(client, token)
    eid = client.post(f"/api/cases/{cid}/evidence", headers=auth(token),
                      files={"file": ("agreement.txt", AGREEMENT.encode())}).json()["id"]
    wait_evidence(client, token, cid)
    lines = client.get(f"/api/cases/{cid}/evidence/{eid}/lines", headers=auth(token)).json()
    assert lines["file"]["total_lines"] >= 6
    assert lines["lines"][0]["text"].startswith("RENTAL AGREEMENT")
    assert lines["lines"][0]["ref"] and lines["lines"][0]["record_type"]
    v = client.get(f"/api/cases/{cid}/evidence/{eid}/verify", headers=auth(token)).json()
    assert v["integrity"] == "VERIFIED"


def test_evidence_integrity_warning_on_change(client):
    token = login(client)
    cid = _case(client, token)
    eid = client.post(f"/api/cases/{cid}/evidence", headers=auth(token),
                      files={"file": ("notes.txt", b"line one\nline two\n")}).json()["id"]
    wait_evidence(client, token, cid)
    from app.db import db
    with db() as c:
        path = c.execute("SELECT stored_path FROM evidence WHERE id=?", (eid,)).fetchone()[0]
    with open(path, "ab") as f:
        f.write(b"tampered\n")
    v = client.get(f"/api/cases/{cid}/evidence/{eid}/verify", headers=auth(token)).json()
    assert v["integrity"] == "WARNING"


def test_evidence_access_is_scoped(client):
    officer = login(client)
    cid = _case(client, officer)
    respondent = login(client, "respondent")
    assert client.post(f"/api/cases/{cid}/evidence", headers=auth(respondent),
                       files={"file": ("a.txt", b"x\n")}).status_code == 404
    assert client.get(f"/api/cases/{cid}/evidence", headers=auth(respondent)).status_code == 404
