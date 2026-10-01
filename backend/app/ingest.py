"""Evidence ingestion: safe storage, SHA-256, E-references, background parsing.

Evidence is treated as untrusted content. Files are copied to disk with a sanitised name,
hashed, and only then parsed into records. Parsing never executes or renders the file, and
nothing in a document is ever interpreted as an instruction.
"""
import hashlib
import json
import re
import shutil
import threading
from datetime import datetime
from pathlib import Path

from . import audit
from .config import get_settings
from .db import db
from .integrity import sha256_file
from .ledger import append_integrity, now_iso
from .nlp import canonical, extract_facts
from .parsers import SUPPORTED, ParseError, parse_file

INGEST_LOCK = threading.Lock()


class UploadError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def safe_name(name: str) -> str:
    base = Path((name or "").replace("\\", "/")).name
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).lstrip(".")
    return base[:120] or "evidence.bin"


def _next_ref(conn, case_id: str, prefix: str, width: int = 3) -> str:
    key = f"{case_id}:evidence"
    row = conn.execute("SELECT value FROM counters WHERE name=?", (key,)).fetchone()
    value = (row["value"] if row else 0) + 1
    if row:
        conn.execute("UPDATE counters SET value=? WHERE name=?", (value, key))
    else:
        conn.execute("INSERT INTO counters(name, value) VALUES(?,?)", (key, value))
    return f"{prefix}-{value:0{width}d}"


def store_upload(case_id: str, filename: str, stream, *, uploader_id: int | None = None,
                 description: str = "", related_party_id: int | None = None,
                 related_claim_id: int | None = None) -> dict:
    """Stream to disk enforcing the size limit, hash, and register an evidence row."""
    s = get_settings()
    name = safe_name(filename)
    ext = Path(name).suffix.lower()
    if ext not in SUPPORTED:
        raise UploadError(415, f"UNSUPPORTED FILE TYPE '{ext or '(none)'}'. Accepted: {', '.join(sorted(SUPPORTED))}")
    dest_dir = (s.upload_dir / safe_name(case_id)).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    tmp = dest_dir / f".incoming_{threading.get_ident()}_{name}"
    h, size = hashlib.sha256(), 0
    try:
        with open(tmp, "wb") as out:
            while chunk := stream.read(1 << 20):
                size += len(chunk)
                if size > s.max_upload_bytes:
                    raise UploadError(413, f"FILE EXCEEDS {s.max_upload_bytes // (1 << 20)} MB LIMIT")
                h.update(chunk)
                out.write(chunk)
        if size == 0:
            raise UploadError(400, "EMPTY FILE")
        digest = h.hexdigest()
        with db() as c:
            dup = c.execute("SELECT id, evidence_ref, filename FROM evidence WHERE case_id=? AND sha256=?", (case_id, digest)).fetchone()
            if dup:
                raise UploadError(409, f"DUPLICATE: identical SHA-256 already stored as {dup['evidence_ref']} ({dup['filename']})")
            final = dest_dir / f"{digest[:12]}_{name}"
            if final.resolve().parent != dest_dir:
                raise UploadError(400, "INVALID FILE NAME")
            shutil.move(str(tmp), final)
            ref = _next_ref(c, case_id, "E")
            cur = c.execute(
                "INSERT INTO evidence(case_id, evidence_ref, filename, stored_path, source_type, media_type, file_size,"
                " sha256, uploader_id, uploaded_at, description, related_party_id, related_claim_id, status)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (case_id, ref, name, str(final), "UNKNOWN", ext.lstrip(".").upper(), size, digest, uploader_id,
                 now_iso(), description, related_party_id, related_claim_id, "HASHED"))
            eid = cur.lastrowid
            file_hash = append_integrity(c, case_id=case_id, kind="EVIDENCE", object_type="evidence",
                                         object_id=ref, object_hash=digest)
            audit.record(c, None, "EVIDENCE_UPLOADED", case_id=case_id, object_type="evidence", object_id=ref,
                         new_state="HASHED", detail=f"{name} sha256={digest[:16]}…")
            return {"id": eid, "evidence_ref": ref, "sha256": digest, "filename": name, "file_hash": file_hash}
    finally:
        if tmp.exists():
            tmp.unlink()


def ingest_evidence(evidence_id: int) -> None:
    """Parse a stored evidence file into records. Runs in a worker; errors are recorded, never raised."""
    with INGEST_LOCK:
        with db() as c:
            row = c.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
            if not row:
                return
            c.execute("UPDATE evidence SET status='PARSING' WHERE id=?", (evidence_id,))
        try:
            res = parse_file(Path(row["stored_path"]), row["filename"])
        except ParseError as e:
            _fail(evidence_id, str(e))
            return
        except Exception as e:  # noqa: BLE001
            _fail(evidence_id, f"PARSER FAILURE: {type(e).__name__}: {e}")
            return
        try:
            with db() as c:
                counters: dict[str, int] = {}
                for (prefix,) in {(r.prefix,) for r in res.records}:
                    m = c.execute("SELECT value FROM counters WHERE name=?", (f"{row['case_id']}:rec:{prefix}",)).fetchone()
                    counters[prefix] = m["value"] if m else 0
                rows, facts_entities, amounts, dates = [], [], [], []
                for r in res.records:
                    counters[r.prefix] += 1
                    ref = f"{r.prefix}-{counters[r.prefix]:03d}"
                    norm = {"fields": r.fields, "typed": r.typed, "text_fields": r.text_fields, "assoc": r.assoc,
                            "summary": r.summary, "time_precision": r.time_precision}
                    rows.append((row["case_id"], evidence_id, ref, r.record_type, r.event_time, r.line_no, r.line_end,
                                 r.raw_text, json.dumps(norm, default=str)))
                    facts = extract_facts(r.raw_text)
                    for ent in facts["entities"]:
                        if ent["canonical"]:
                            facts_entities.append(ent)
                    amounts.extend(facts["amounts"])
                    dates.extend(facts["dates"])
                c.executemany(
                    "INSERT INTO records(case_id, evidence_id, ref, record_type, event_time, line_no, line_end, raw_text, normalized_json)"
                    " VALUES(?,?,?,?,?,?,?,?,?)", rows)
                for prefix, value in counters.items():
                    c.execute("INSERT INTO counters(name, value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value",
                              (f"{row['case_id']}:rec:{prefix}", value))
                extracted = _dedupe_facts(facts_entities, amounts, dates)
                c.execute("UPDATE evidence SET status='PARSED', source_type=?, record_count=?, line_count=?, message=?, extracted_json=?"
                          " WHERE id=?",
                          (res.source_type, len(rows), res.line_count, "; ".join(res.warnings) or None,
                           json.dumps(extracted, default=str), evidence_id))
                audit.record(c, None, "EVIDENCE_PROCESSED", case_id=row["case_id"], object_type="evidence",
                             object_id=row["evidence_ref"], new_state="PARSED",
                             detail=f"{len(rows)} records; source={res.source_type}")
        except Exception as e:  # noqa: BLE001
            _fail(evidence_id, f"DATABASE FAILURE: {type(e).__name__}: {e}")


def _dedupe_facts(entities, amounts, dates) -> dict:
    seen_e, seen_a, seen_d = set(), set(), set()
    ents, amts, dts = [], [], []
    for e in entities:
        k = (e["type"], e["canonical"])
        if k not in seen_e:
            seen_e.add(k)
            ents.append(e)
    for a in amounts:
        if a not in seen_a:
            seen_a.add(a)
            amts.append(a)
    for d in dates:
        k = (d["value"], d["iso"])
        if k not in seen_d:
            seen_d.add(k)
            dts.append(d)
    return {"entities": ents[:400], "amounts": amts[:200], "dates": dts[:200]}


def _fail(evidence_id: int, msg: str) -> None:
    with db() as c:
        row = c.execute("SELECT case_id, evidence_ref FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        c.execute("UPDATE evidence SET status='ERROR', message=? WHERE id=?", (msg, evidence_id))
        if row:
            audit.record(c, None, "EVIDENCE_PROCESSING_FAILED", case_id=row["case_id"], object_type="evidence",
                         object_id=row["evidence_ref"], new_state="ERROR", detail=msg[:300])


def recompute_extraction(conn, case_id: str) -> int:
    """Re-derive the aggregated extracted facts for every evidence item in a case."""
    n = 0
    for e in conn.execute("SELECT id, evidence_ref FROM evidence WHERE case_id=?", (case_id,)).fetchall():
        ents, amounts, dates = [], [], []
        for (raw,) in conn.execute("SELECT raw_text FROM records WHERE evidence_id=?", (e["id"],)):
            facts = extract_facts(raw)
            ents.extend(x for x in facts["entities"] if x["canonical"])
            amounts.extend(facts["amounts"])
            dates.extend(facts["dates"])
        conn.execute("UPDATE evidence SET extracted_json=? WHERE id=?",
                     (json.dumps(_dedupe_facts(ents, amounts, dates), default=str), e["id"]))
        n += 1
    return n


def verify_evidence_integrity(conn, case_id: str) -> dict:
    """Re-hash every stored file and compare with the hash recorded at intake."""
    files = [dict(r) for r in conn.execute("SELECT * FROM evidence WHERE case_id=?", (case_id,))]
    bad = []
    for f in files:
        p = Path(f["stored_path"])
        ok = p.exists() and sha256_file(p) == f["sha256"]
        conn.execute("UPDATE evidence SET verify_status=?, verified_at=? WHERE id=?",
                     ("VERIFIED" if ok else "MISMATCH", datetime.now().astimezone().isoformat(timespec="seconds"), f["id"]))
        if not ok:
            bad.append(f["evidence_ref"])
    return {"total": len(files), "verified": len(files) - len(bad), "mismatch": bad}


# keep canonical import used by callers
_ = canonical
