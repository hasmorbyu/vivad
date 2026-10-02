"""Case timeline progression endpoint."""
from fastapi import APIRouter, Depends

from ..auth import assert_case_access, get_current_user
from ..db import db
from ..intel.journey import build_journey

router = APIRouter(prefix="/api/cases/{case_id}", tags=["journey"])


@router.get("/journey")
def journey(case_id: str, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        return build_journey(c, case_id)
