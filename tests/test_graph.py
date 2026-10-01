"""Phase 4: the case graph is a view of the case model with provenance on every edge."""
from conftest import auth, login, wait_analysis

from test_intelligence import _seed


def test_graph_contains_case_model_nodes_and_edges(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    g = client.get(f"/api/cases/{cid}/graph", headers=auth(token)).json()
    kinds = {n["data"]["kind"] for n in g["nodes"]}
    assert {"case", "party", "claim", "evidence", "event", "contradiction", "law"} <= kinds
    assert g["edges"]
    labels = {e["data"]["label"] for e in g["edges"]}
    assert {"INVOLVES", "ASSERTS", "SUPPORTS"} <= labels
    ids = {n["data"]["id"] for n in g["nodes"]}
    for e in g["edges"]:
        assert e["data"]["source"] in ids and e["data"]["target"] in ids and e["data"]["label"]
    ev = next(n["data"] for n in g["nodes"] if n["data"]["kind"] == "evidence")
    assert ev["evidence_id"] and "evidence_ref" not in ev  # evidence handled by id in graph


def test_graph_filter_and_access(client):
    token = login(client)
    cid, _, _ = _seed(client, token)
    client.post(f"/api/cases/{cid}/analyze", headers=auth(token))
    wait_analysis(client, token, cid)
    g = client.get(f"/api/cases/{cid}/graph", params={"kinds": "claim,evidence"}, headers=auth(token)).json()
    assert {n["data"]["kind"] for n in g["nodes"]} == {"claim", "evidence"}
    respondent = login(client, "respondent")
    assert client.get(f"/api/cases/{cid}/graph", headers=auth(respondent)).status_code == 404
