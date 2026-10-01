"""Legal reference loading and concept association.

References are loaded from a curated, source-attributed dataset. Association is a
deterministic keyword/concept match over the case text and is fully explainable: each case
shows why a provision was surfaced. This is reference material for humans, not legal advice.
"""
import json
import re
from pathlib import Path

from ..config import get_settings

WORD = re.compile(r"[A-Za-z][A-Za-z-]{2,}")


def load_dataset(conn) -> int:
    path = Path(get_settings().legal_dir) / "india.json"
    if not path.exists():
        return 0
    try:
        doc = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return 0
    n = 0
    for p in doc.get("provisions", []):
        conn.execute(
            "INSERT INTO legal_references(id, jurisdiction, act, section, title, description, source_url, last_verified, concepts, disclaimer)"
            " VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET"
            " act=excluded.act, section=excluded.section, title=excluded.title, description=excluded.description,"
            " source_url=excluded.source_url, last_verified=excluded.last_verified, concepts=excluded.concepts, disclaimer=excluded.disclaimer",
            (p["id"], doc.get("jurisdiction", "India"), p["act"], p["section"], p["title"], p["description"],
             p["source_url"], doc.get("last_reviewed", ""), json.dumps(p.get("concepts", [])), doc.get("disclaimer", "")))
        n += 1
    return n


def _corpus(conn, case_id: str) -> str:
    parts = []
    case = conn.execute("SELECT title, description, category, requested_resolution FROM cases WHERE id=?", (case_id,)).fetchone()
    if case:
        parts += [case["title"] or "", case["description"] or "", case["category"] or "", case["requested_resolution"] or ""]
    for s in conn.execute("SELECT claim, what, evidence_support FROM statements WHERE case_id=?", (case_id,)):
        parts += [s["claim"] or "", s["what"] or "", s["evidence_support"] or ""]
    for c in conn.execute("SELECT text FROM claims WHERE case_id=?", (case_id,)):
        parts.append(c["text"] or "")
    for e in conn.execute("SELECT extracted_json FROM evidence WHERE case_id=?", (case_id,)):
        try:
            data = json.loads(e["extracted_json"] or "{}")
        except json.JSONDecodeError:
            continue
        for ent in data.get("entities", []):
            if ent.get("type") in ("DOCUMENT_ID", "ORGANIZATION"):
                parts.append(str(ent.get("value", "")))
    return " ".join(parts).lower()


def associate(conn, case_id: str, top: int = 6) -> int:
    conn.execute("DELETE FROM case_legal_refs WHERE case_id=?", (case_id,))
    corpus = _corpus(conn, case_id)
    corpus_words = set(WORD.findall(corpus))
    if not corpus_words:
        return 0
    scored = []
    for r in conn.execute("SELECT * FROM legal_references"):
        concepts = json.loads(r["concepts"] or "[]")
        # a concept matches when the phrase appears, or all of its words are present
        hits = [c for c in concepts if c in corpus or all(w in corpus_words for w in c.split())]
        if hits:
            scored.append((len(hits), r, hits))
    scored.sort(key=lambda x: -x[0])
    created = 0
    for _, r, hits in scored[:top]:
        relevance = (f"Detected concepts: {', '.join(sorted(set(hits)))}. "
                     f"Potentially related legal area: {r['act']}, section {r['section']} — {r['title']}. "
                     "This is reference material only; it does not establish liability.")
        conn.execute(
            "INSERT INTO case_legal_refs(case_id, legal_reference_id, relevance, concepts, origin, status, created_at)"
            " VALUES(?,?,?,?,?,?,?)",
            (case_id, r["id"], relevance, json.dumps(sorted(set(hits))), "DETERMINISTIC", "POTENTIALLY_RELEVANT", None))
        created += 1
    return created
