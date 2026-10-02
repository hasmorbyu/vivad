"""Timeline progression model: structural stages, statuses, branches and access scoping."""
from conftest import auth, login, wait_analysis

from test_intelligence import _seed


def test_journey_model_from_real_case_data(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    j = client.get(f"/api/cases/{cid}/journey", headers=auth(token)).json()

    assert j["header"]["case_id"] == cid
    assert j["stages"] and j["stages"][0]["kind"] == "FILED"
    statuses = [s["status"] for s in j["stages"]]
    assert statuses.count("CURRENT") == 1
    assert statuses[0] == "COMPLETED"
    assert j["header"]["counts"]["completed"] + j["header"]["counts"]["current"] + j["header"]["counts"]["upcoming"] == len(j["stages"])
    # ordered chronologically where dates exist
    dated = [s["date"] for s in j["stages"] if s["date"]]
    assert dated == sorted(dated)
    # evidence stage carries branch groups
    ev = next(s for s in j["stages"] if s["kind"] == "EVIDENCE_SUBMITTED")
    assert ev["branches"] and sum(b["count"] for b in ev["branches"]) == 2
    assert all(b["evidence"] for b in ev["branches"])
    # every stage exposes the required structure
    for s in j["stages"]:
        for key in ("id", "kind", "title", "description", "date", "status",
                    "participants", "evidence", "legalReferences", "documents",
                    "relatedEvents", "actionRequired", "dueDate"):
            assert key in s, key


def test_journey_flags_conditions(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    j = client.get(f"/api/cases/{cid}/journey", headers=auth(token)).json()
    contra = next((s for s in j["stages"] if s["kind"] == "CONTRADICTIONS"), None)
    # unresolved contradictions are flagged critical, with an explanation
    assert contra is not None and contra["flag"] == "CRITICAL" and contra["flagReason"]


def test_journey_is_access_scoped(client):
    officer = login(client)
    cid, _, _ = _seed(client, officer)
    respondent = login(client, "respondent")
    assert client.get(f"/api/cases/{cid}/journey", headers=auth(respondent)).status_code == 404
