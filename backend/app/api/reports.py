"""Report export (JSON + PDF) and the case integrity verification endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..anchor import anchor_head
from ..auth import assert_case_access, get_current_user
from ..config import get_settings
from ..db import db
from ..ingest import verify_evidence_integrity
from ..ledger import verify_audit_chain, verify_integrity_chain
from ..reports.pdf import build_pdf
from ..reports.serialize import build_report

router = APIRouter(prefix="/api/cases/{case_id}", tags=["report"])


@router.get("/report.json")
def report_json(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        return build_report(c, case_id)


@router.get("/report.pdf")
def report_pdf(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        try:
            pdf = build_pdf(c, case_id)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(500, f"REPORT GENERATION FAILED: {type(e).__name__}: {e}")
    s = get_settings()
    s.report_dir.mkdir(parents=True, exist_ok=True)
    (s.report_dir / f"VIVAD_{case_id}.pdf").write_bytes(pdf)
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="VIVAD_{case_id}.pdf"'})


@router.get("/integrity")
def integrity(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        audit_chain = verify_audit_chain(c)
        integrity_chain = verify_integrity_chain(c)
        evidence = verify_evidence_integrity(c, case_id)
        anchor = anchor_head(c)
        ok = audit_chain["ok"] and integrity_chain["ok"] and not evidence["mismatch"]
        return {
            "status": "VERIFIED" if ok else "WARNING",
            "audit_chain": audit_chain,
            "integrity_chain": integrity_chain,
            "evidence": evidence,
            "anchor": anchor,
            "note": "SHA-256 verifies integrity and detects change. It does not by itself establish chain of custody or authorship.",
        }
