import sys
from pathlib import Path

import pytest

VIVAD = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(VIVAD / "backend"))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("VIVAD_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VIVAD_REPORT_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("VIVAD_SEED_DEMO_USERS", "1")
    from fastapi.testclient import TestClient
    from app.main import app
    # The repository .env is loaded at import via setdefault; blank the keys afterwards so
    # get_settings() (read per request) reports AI as unavailable for deterministic tests.
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GROQ_API_KEY", "")
    with TestClient(app) as c:
        yield c


def login(client, username="officer", password="vivad123"):
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def wait_analysis(client, token, case_id, timeout=60):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        s = client.get(f"/api/cases/{case_id}/analyze/status", headers=auth(token)).json()
        if s["state"] != "RUNNING":
            return s
        time.sleep(0.2)
    raise TimeoutError("analysis")


def wait_evidence(client, token, case_id, timeout=30):
    import time
    deadline = time.time() + timeout
    while time.time() < deadline:
        files = client.get(f"/api/cases/{case_id}/evidence", headers=auth(token)).json()
        if files and all(f["status"] in ("PARSED", "ERROR") for f in files):
            return files
        time.sleep(0.2)
    raise TimeoutError("evidence parsing")
