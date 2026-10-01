"""Liveness and integration-status endpoint."""
from fastapi import APIRouter

from ..config import get_settings
from ..ledger import verify_audit_chain, verify_integrity_chain
from ..db import db

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health():
    s = get_settings()
    if s.gemini_api_key:
        provider, model = "gemini", s.gemini_model
    elif s.groq_api_key:
        provider, model = "groq", s.groq_model
    else:
        provider, model = "none", ""
    with db() as c:
        audit_chain = verify_audit_chain(c)
        integrity_chain = verify_integrity_chain(c)
    return {
        "status": "ok",
        "app": "VIVAD",
        "ai": {"provider": provider, "configured": provider != "none", "model": model},
        "video": {"provider": s.video_provider},
        "integrity": {"audit_chain": audit_chain, "integrity_chain": integrity_chain},
    }
