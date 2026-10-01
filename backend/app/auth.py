"""Authentication and role-based authorization.

Passwords are hashed with PBKDF2-HMAC-SHA256 (standard library only). Sessions are opaque
random tokens with an expiry. Authorization is always enforced server-side: the frontend
only hides what the API would refuse anyway.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Header, HTTPException

from .config import ROLES, get_settings
from .db import db

PBKDF2_ITERATIONS = 200_000
STAFF_ROLES = ("CASE_OFFICER", "REVIEWER", "CHAIR", "ADMIN")
ALL_CASE_ROLES = STAFF_ROLES + ("CITIZEN", "RESPONDENT")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return digest, salt


def verify_password(password: str, password_hash: str, salt: str) -> bool:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITERATIONS).hex()
    return secrets.compare_digest(digest, password_hash)


def create_user(conn, username: str, password: str, role: str, display_name: str = "", email: str = "") -> int:
    if role not in ROLES:
        raise ValueError(f"unknown role: {role}")
    digest, salt = hash_password(password)
    cur = conn.execute(
        "INSERT INTO users(username, display_name, email, role, password_hash, created_at) VALUES(?,?,?,?,?,?)",
        (username.strip().lower(), display_name or username, email, role, f"{salt}${digest}",
         _now().isoformat(timespec="seconds")))
    return cur.lastrowid


def create_session(conn, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    created = _now()
    expires = created + timedelta(hours=get_settings().session_hours)
    conn.execute("INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES(?,?,?,?)",
                 (token, user_id, created.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")))
    return token


def revoke_session(conn, token: str) -> None:
    conn.execute("UPDATE sessions SET revoked=1 WHERE token=?", (token,))


def authenticate(conn, username: str, password: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE username=? AND active=1", (username.strip().lower(),)).fetchone()
    if not row:
        return None
    parts = (row["password_hash"] or "").split("$", 1)
    if len(parts) != 2 or not verify_password(password, parts[1], parts[0]):
        return None
    return public_user(dict(row))


def user_for_token(conn, token: str | None) -> dict | None:
    if not token:
        return None
    row = conn.execute(
        "SELECT u.*, s.expires_at, s.revoked FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?",
        (token,)).fetchone()
    if not row or row["revoked"] or not row["active"]:
        return None
    try:
        if datetime.fromisoformat(row["expires_at"]) < _now():
            return None
    except (TypeError, ValueError):
        return None
    return public_user(dict(row))


def public_user(u: dict) -> dict:
    return {"id": u["id"], "username": u["username"], "name": u.get("display_name") or u["username"],
            "role": u["role"], "email": u.get("email") or ""}


def _bearer(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return authorization.strip()


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    with db() as c:
        user = user_for_token(c, _bearer(authorization))
    if not user:
        raise HTTPException(401, "AUTHENTICATION REQUIRED")
    return user


def get_optional_user(authorization: str | None = Header(default=None)) -> dict | None:
    with db() as c:
        return user_for_token(c, _bearer(authorization))


def require_role(*roles: str):
    def dependency(user: dict = Depends(get_current_user)) -> dict:
        if roles and user["role"] not in roles:
            raise HTTPException(403, f"ROLE {user['role']} MAY NOT PERFORM THIS ACTION")
        return user
    return dependency


def can_access_case(conn, case_id: str, user: dict) -> bool:
    if not user:
        return False
    if user["role"] in STAFF_ROLES:
        return True
    row = conn.execute("SELECT created_by FROM cases WHERE id=?", (case_id,)).fetchone()
    if not row:
        return False
    if row["created_by"] == user["id"]:
        return True
    return conn.execute("SELECT 1 FROM parties WHERE case_id=? AND user_id=? LIMIT 1",
                        (case_id, user["id"])).fetchone() is not None


def assert_case_access(conn, case_id: str, user: dict) -> None:
    if not can_access_case(conn, case_id, user):
        # 404 rather than 403 so a user cannot probe for the existence of other cases
        raise HTTPException(404, f"CASE NOT FOUND: {case_id}")
