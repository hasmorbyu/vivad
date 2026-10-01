"""Phase 5: human review, evidence requests, hearings, meetings and hearing notes."""
from conftest import auth, login, wait_analysis

from test_intelligence import _seed


def _analysed(client, token):
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    return cid


def test_review_accept_and_history_and_rbac(client):
    token = login(client)
    cid = _analysed(client, token)
    findings = client.get(f"/api/cases/{cid}/reviews", headers=auth(token)).json()["findings"]
    assert findings
    fid = findings[0]["id"]
    r = client.post(f"/api/cases/{cid}/reviews", headers=auth(token),
                    json={"finding_id": fid, "action": "ACCEPT", "comment": "checked against E-001"})
    assert r.status_code == 201 and r.json()["human_status"] == "ACCEPT"
    hist = client.get(f"/api/cases/{cid}/reviews", headers=auth(token)).json()["history"]
    assert hist and hist[0]["action"] == "ACCEPT" and hist[0]["reviewer_role"] == "CASE_OFFICER"
    # a citizen may not review findings
    citizen = login(client, "citizen")
    r2 = client.post(f"/api/cases/{cid}/reviews", headers=auth(citizen), json={"finding_id": fid, "action": "ACCEPT"})
    assert r2.status_code in (403, 404)


def test_edit_replaces_body(client):
    token = login(client)
    cid = _analysed(client, token)
    fid = client.get(f"/api/cases/{cid}/reviews", headers=auth(token)).json()["findings"][0]["id"]
    r = client.post(f"/api/cases/{cid}/reviews", headers=auth(token),
                    json={"finding_id": fid, "action": "EDIT", "edited_body": "Reviewer-corrected wording."})
    assert r.status_code == 201 and r.json()["body"] == "Reviewer-corrected wording."


def test_evidence_request_notifies_linked_party(client):
    officer = login(client)
    respondent = login(client, "respondent")
    me = client.get("/api/auth/me", headers=auth(respondent)).json()
    cid, _, _ = _seed(client, officer)
    # link the respondent party row to the respondent user
    parties = client.get(f"/api/cases/{cid}/parties", headers=auth(officer)).json()
    rid = next(p["id"] for p in parties if p["role"] == "RESPONDENT")
    client.patch(f"/api/cases/{cid}/parties/{rid}", headers=auth(officer),
                 json={"name": "Neel Kapoor", "role": "RESPONDENT", "user_id": me["id"]})
    r = client.post(f"/api/cases/{cid}/evidence-requests", headers=auth(officer),
                    json={"about": "Please provide the repair invoice.", "party_id": rid})
    assert r.status_code == 201
    case = client.get(f"/api/cases/{cid}", headers=auth(officer)).json()
    assert case["status"] == "EVIDENCE_REQUESTED"
    notes = client.get("/api/notifications", headers=auth(respondent)).json()
    assert notes["unread"] >= 1 and any(n["kind"] == "EVIDENCE_REQUEST" for n in notes["items"])


def test_hearing_schedule_join_and_notes(client):
    token = login(client)
    uid = client.get("/api/auth/me", headers=auth(token)).json()["id"]
    cid = _audience_case(client, token)
    r = client.post(f"/api/cases/{cid}/hearings", headers=auth(token),
                    json={"scheduled_at": "2026-10-03T11:30:00+05:30", "duration_min": 30, "agenda": "Review deposit deduction"})
    assert r.status_code == 201, r.text
    hearing = r.json()
    assert hearing["provider"] == "jitsi" and hearing["room_id"].startswith("vivad-")
    assert hearing["participants"] and any(p["role"] == "RESPONDENT" for p in hearing["participants"])
    case = client.get(f"/api/cases/{cid}", headers=auth(token)).json()
    assert case["status"] == "HEARING_SCHEDULED"

    hid = hearing["id"]
    join = client.post(f"/api/hearings/{hid}/join", headers=auth(token)).json()
    assert join["meeting"]["provider"] == "jitsi" and join["meeting"]["url"].startswith("https://meet.jit.si/")
    assert join["hearing"]["participants"]

    note = client.post(f"/api/hearings/{hid}/notes", headers=auth(token),
                       json={"issue": "Deduction", "party_a": "Paid full deposit", "next_action": "Request invoice"}).json()
    assert note["body"]["issue"] == "Deduction"
    notes = client.get(f"/api/hearings/{hid}/notes", headers=auth(token)).json()
    assert len(notes) == 1 and notes[0]["author_id"] == uid and notes[0]["created_at"]

    client.patch(f"/api/hearings/{hid}", headers=auth(token), json={"status": "COMPLETED"})
    assert client.get(f"/api/hearings/{hid}", headers=auth(token)).json()["status"] == "COMPLETED"


def _audience_case(client, token):
    cid, _, _ = _seed(client, token)
    return cid
