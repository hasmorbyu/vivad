"""Case graph via NetworkX, serialised to Cytoscape elements.

The graph is a view of the case model: parties assert claims; claims are supported by
evidence; evidence records events; contradictions connect the claims and evidence they
concern; legal references and hearings attach to the case. Every edge carries its
provenance and is labelled with what it means — a graph edge is never proof.
"""
import json

import networkx as nx

from ..services import parse_json


def _short(text: str, n: int = 60) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def build_graph(conn, case_id: str, kinds: str | None = None) -> dict:
    keep = set(kinds.split(",")) if kinds else None
    g = nx.MultiDiGraph()

    def node(nid, kind, ntype, label, **extra):
        if keep and kind not in keep:
            return
        g.add_node(nid, id=nid, kind=kind, type=ntype, label=label, **extra)

    def edge(src, dst, label, **extra):
        if src in g and dst in g:
            g.add_edge(src, dst, key=f"{src}->{dst}:{label}", label=label, **extra)

    case = conn.execute("SELECT * FROM cases WHERE id=?", (case_id,)).fetchone()
    if not case:
        return {"nodes": [], "edges": []}
    node("CASE", "case", "CASE", case["id"], case_id=case_id, detail=case["title"])

    for p in conn.execute("SELECT * FROM parties WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"P{p['id']}"
        node(nid, "party", "PARTY", p["name"], party_id=p["id"], detail=f"{p['role']}" + (f" · {p['contact']}" if p["contact"] else ""))
        edge("CASE", nid, "INVOLVES")

    for c in conn.execute("SELECT * FROM claims WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"CL{c['id']}"
        node(nid, "claim", "CLAIM", f"{c['claim_ref']} · {_short(c['text'], 40)}", claim_id=c["id"],
             detail=f"{c['status']}" + (f" · ₹{c['amount']:,.0f}" if c["amount"] else ""))
        if c["party_id"]:
            edge(f"P{c['party_id']}", nid, "ASSERTS")

    for e in conn.execute("SELECT * FROM evidence WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"E{e['id']}"
        node(nid, "evidence", "EVIDENCE", f"{e['evidence_ref']} · {_short(e['filename'], 28)}", evidence_id=e["id"],
             detail=f"{e['source_type']} · {e['status']}")
        edge(nid, "CASE", "PART_OF")

    for r in conn.execute(
        "SELECT er.claim_id, er.evidence_id, er.relationship FROM evidence_references er WHERE er.case_id=?", (case_id,)):
        edge(f"E{r['evidence_id']}", f"CL{r['claim_id']}", "SUPPORTS")

    for ev in conn.execute("SELECT * FROM events WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"EV{ev['id']}"
        node(nid, "event", "EVENT", f"{ev['event_ref']} · {_short(ev['title'], 34)}", event_id=ev["id"],
             detail=f"{ev['event_type']} · {ev['event_time']}")
        if ev["evidence_id"]:
            edge(f"E{ev['evidence_id']}", nid, "RECORDS")

    for x in conn.execute("SELECT * FROM contradictions WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"C{x['id']}"
        node(nid, "contradiction", "CONTRADICTION", f"{x['contradiction_ref']} · {_short(x['title'], 34)}",
             contradiction_id=x["id"], detail=f"{x['kind']} · {x['verification_status']}")
        if x["claim_a_id"]:
            edge(nid, f"CL{x['claim_a_id']}", "CONCERNS")
        if x["claim_b_id"]:
            edge(nid, f"CL{x['claim_b_id']}", "CONCERNS")
        for eid in parse_json(x["evidence_ids"], []):
            edge(nid, f"E{eid}", "CITES")

    for ref in conn.execute(
        "SELECT clr.id, clr.legal_reference_id, clr.relevance, lr.act, lr.section FROM case_legal_refs clr "
        "JOIN legal_references lr ON lr.id=clr.legal_reference_id WHERE clr.case_id=? ORDER BY clr.id", (case_id,)):
        nid = f"L{ref['id']}"
        node(nid, "law", "LAW", f"{ref['act'].split(',')[0]} s.{ref['section']}", law_id=ref["legal_reference_id"],
             detail=_short(ref["relevance"], 120))
        edge("CASE", nid, "MAY_BE_RELEVANT")

    for h in conn.execute("SELECT * FROM hearings WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"H{h['id']}"
        node(nid, "hearing", "HEARING", f"Hearing · {h['scheduled_at'] or 'unscheduled'}", hearing_id=h["id"], detail=h["status"])
        edge("CASE", nid, "SCHEDULES")

    for d in conn.execute("SELECT * FROM decisions WHERE case_id=? ORDER BY id", (case_id,)):
        nid = f"D{d['id']}"
        node(nid, "decision", "DECISION", f"{d['decision_ref']} · {_short(d['decision'], 30)}", decision_id=d["id"], detail=d["status"])
        edge("CASE", nid, "RESOLVES")

    nodes = [{"data": d} for _, d in g.nodes(data=True)]
    edges = []
    for u, v, key, d in g.edges(keys=True, data=True):
        edges.append({"data": {"id": key, "source": u, "target": v, "label": d.get("label", "")}})
    return {"nodes": nodes, "edges": edges,
            "components": nx.number_weakly_connected_components(g) if g.number_of_nodes() else 0}
