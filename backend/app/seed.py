"""Demo users, one per role, created at startup if absent.

Passwords are for local demonstration only and are documented in the README. Real
deployments must replace them; this seeder never overwrites an existing user.
"""
from .auth import create_user
from .db import db

DEMO_PASSWORD = "vivad123"

DEMO_USERS = [
    ("admin", "ADMIN", "System Administrator"),
    ("officer", "CASE_OFFICER", "Case Officer 17"),
    ("reviewer", "REVIEWER", "Committee Member Rao"),
    ("chair", "CHAIR", "Chairperson Iyer"),
    ("citizen", "CITIZEN", "Aarav Menon"),
    ("respondent", "RESPONDENT", "Neel Kapoor"),
]


def seed_demo_users() -> list[str]:
    created = []
    with db() as c:
        for username, role, name in DEMO_USERS:
            exists = c.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone()
            if not exists:
                create_user(c, username, DEMO_PASSWORD, role, display_name=name, email=f"{username}@vivad.example")
                created.append(username)
    return created
