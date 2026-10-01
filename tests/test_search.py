"""Phase 7: global search and access scoping."""
from conftest import auth, login, wait_analysis

from test_intelligence import _seed


def test_search_finds_case_evidence_and_claims(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    r = client.get("/api/search", params={"q": "deposit"}, headers=auth(token)).json()["results"]
    assert any(c["id"] == cid for c in r["cases"])
    assert r["claims"]  # claims mention the deposit
    r2 = client.get("/api/search", params={"q": "agreement"}, headers=auth(token)).json()["results"]
    assert r2["evidence"] and r2["evidence"][0]["evidence_ref"] == "E-001"


def test_search_is_access_scoped(client):
    officer = login(client)
    cid, _, _ = _seed(client, officer)
    respondent = login(client, "respondent")
    r = client.get("/api/search", params={"q": "deposit"}, headers=auth(respondent)).json()["results"]
    assert all(c["id"] != cid for c in r["cases"])


def test_search_legal_dataset_is_available(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)  # the dataset is loaded into the DB during analysis
    r = client.get("/api/search", params={"q": "contract"}, headers=auth(token)).json()["results"]
    assert r["legal"]
