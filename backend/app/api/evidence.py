"""Evidence intake, listing, detail, integrity, preview and record reader."""
import mimetypes
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from .. import ingest
from ..auth import assert_case_access, get_current_user
from ..db import db
from ..services import evidence_detail, evidence_rows

router = APIRouter(prefix="/api/cases/{case_id}/evidence", tags=["evidence"])


@router.get("")
def list_evidence(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        rows = evidence_rows(c, case_id)
        for r in rows:
            r.pop("stored_path", None)
            r.pop("extracted_json", None)
        return rows


@router.post("", status_code=202)
def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    description: str = Form(""),
    related_party_id: int | None = Form(None),
    related_claim_id: int | None = Form(None),
    user: dict = Depends(get_current_user),
):
    with db() as c:
        assert_case_access(c, case_id, user)
        if related_party_id is not None and not c.execute("SELECT 1 FROM parties WHERE id=? AND case_id=?", (related_party_id, case_id)).fetchone():
            raise HTTPException(422, "RELATED PARTY DOES NOT BELONG TO THIS CASE")
    try:
        rec = ingest.store_upload(case_id, file.filename or "evidence", file.file, uploader_id=user["id"],
                                  description=description, related_party_id=related_party_id, related_claim_id=related_claim_id)
    except ingest.UploadError as e:
        raise HTTPException(e.status, e.message)
    threading.Thread(target=ingest.ingest_evidence, args=(rec["id"],), daemon=True).start()
    with db() as c:
        row = dict(c.execute("SELECT * FROM evidence WHERE id=?", (rec["id"],)).fetchone())
        row.pop("stored_path", None)
        row.pop("extracted_json", None)
        return row


@router.get("/{evidence_id}")
def get_evidence(case_id: str, evidence_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        d = evidence_detail(c, case_id, evidence_id)
        if not d:
            raise HTTPException(404, "EVIDENCE NOT FOUND")
        return d


@router.get("/{evidence_id}/file")
def get_file(case_id: str, evidence_id: int, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        row = c.execute("SELECT * FROM evidence WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
    if not row:
        raise HTTPException(404, "EVIDENCE NOT FOUND")
    path = Path(row["stored_path"])
    if not path.exists():
        raise HTTPException(404, "STORED FILE IS MISSING")
    media = mimetypes.guess_type(row["filename"])[0] or "application/octet-stream"
    if media.startswith("text/") or media in ("application/json",):
        media += "; charset=utf-8"
    return FileResponse(path, media_type=media, filename=row["filename"])


@router.get("/{evidence_id}/lines")
def evidence_lines(case_id: str, evidence_id: int, start: int = Query(1, ge=1), count: int = Query(200, ge=1, le=1000),
                   user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        f = c.execute("SELECT * FROM evidence WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
        if not f:
            raise HTTPException(404, "EVIDENCE NOT FOUND")
        recs = c.execute("SELECT ref, line_no, line_end, record_type, event_time FROM records WHERE evidence_id=? AND line_no BETWEEN ? AND ?",
                         (evidence_id, start, start + count)).fetchall()
    path = Path(f["stored_path"])
    if not path.exists():
        raise HTTPException(404, "STORED FILE IS MISSING")
    from ..parsers.common import read_text
    try:
        lines = read_text(path).splitlines()
    except Exception:  # noqa: BLE001 — binary evidence has no line reader
        lines = []
    chunk = lines[start - 1: start - 1 + count]
    refs = {}
    for r in recs:
        for ln in range(r["line_no"], (r["line_end"] or r["line_no"]) + 1):
            refs.setdefault(ln, {"ref": r["ref"], "record_type": r["record_type"], "event_time": r["event_time"]})
    return {"file": {"id": f["id"], "evidence_ref": f["evidence_ref"], "filename": f["filename"], "sha256": f["sha256"],
                     "source_type": f["source_type"], "total_lines": len(lines), "previewable": bool(lines)},
            "start": start,
            "lines": [{"n": start + i, "text": t, "ref": (refs.get(start + i) or {}).get("ref"),
                       "record_type": (refs.get(start + i) or {}).get("record_type"),
                       "event_time": (refs.get(start + i) or {}).get("event_time")} for i, t in enumerate(chunk)]}


@router.get("/{evidence_id}/verify")
def verify_one(case_id: str, evidence_id: int, user: dict = Depends(get_current_user)):
    from ..integrity import sha256_file
    with db() as c:
        assert_case_access(c, case_id, user)
        row = c.execute("SELECT * FROM evidence WHERE id=? AND case_id=?", (evidence_id, case_id)).fetchone()
    if not row:
        raise HTTPException(404, "EVIDENCE NOT FOUND")
    path = Path(row["stored_path"])
    ok = path.exists() and sha256_file(path) == row["sha256"]
    return {"evidence_ref": row["evidence_ref"], "integrity": "VERIFIED" if ok else "WARNING",
            "expected": row["sha256"], "reason": None if ok else "The stored file no longer matches the hash recorded at intake."}
