"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .. import audit
from ..auth import authenticate, create_session, get_current_user, public_user, revoke_session
from ..db import db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    return parts[1].strip() if len(parts) == 2 and parts[0].lower() == "bearer" else authorization.strip()


@router.post("/login")
def login(body: LoginIn):
    with db() as c:
        user = authenticate(c, body.username, body.password)
        if not user:
            raise HTTPException(401, "INVALID CREDENTIALS")
        token = create_session(c, user["id"])
        audit.record(c, user, "USER_LOGIN", object_type="user", object_id=user["id"])
        return {"token": token, "user": user}


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    token = _bearer(authorization)
    with db() as c:
        from ..auth import user_for_token
        user = user_for_token(c, token)
        if token:
            revoke_session(c, token)
        if user:
            audit.record(c, user, "USER_LOGOUT", object_type="user", object_id=user["id"])
    return {"ok": True}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return public_user(user)
