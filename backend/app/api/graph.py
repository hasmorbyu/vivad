"""Case graph endpoint."""
from fastapi import APIRouter, Depends

from ..auth import assert_case_access, get_current_user
from ..db import db
from ..graph.builder import build_graph

router = APIRouter(prefix="/api/cases/{case_id}", tags=["graph"])


@router.get("/graph")
def graph(case_id: str, kinds: str | None = None, user: dict = Depends(get_current_user)):
    with db() as c:
        assert_case_access(c, case_id, user)
        return build_graph(c, case_id, kinds)
