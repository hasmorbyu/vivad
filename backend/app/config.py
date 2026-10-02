"""VIVAD runtime configuration. Read at call time so tests can redirect the data dir.

Secrets are read from the repository-root .env (never bundled into the frontend). Every
integration is optional: with no keys VIVAD runs deterministically and labels AI as
unavailable rather than failing.
"""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIVAD_ROOT = Path(__file__).resolve().parents[2]


def _load_dotenv() -> None:
    """Load configuration from the repository-root .env, then vivad/.env, then vivad/.env.local.

    Later files override earlier ones so a local file can refine the shared config, but a
    value already present in the real process environment always wins.
    """
    real_env = set(os.environ)
    for env in (ROOT / ".env", VIVAD_ROOT / ".env", VIVAD_ROOT / ".env.local"):
        if not env.exists():
            continue
        for line in env.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k not in real_env:
                os.environ[k] = v


_load_dotenv()

AIProviderName = str

ROLES = ("CITIZEN", "RESPONDENT", "CASE_OFFICER", "REVIEWER", "CHAIR", "ADMIN")


@dataclass
class Settings:
    data_dir: Path
    db_path: Path
    upload_dir: Path
    report_dir: Path
    legal_dir: Path
    max_upload_bytes: int
    auth_secret: str
    session_hours: int
    gemini_api_key: str
    gemini_model: str
    groq_api_key: str
    groq_model: str
    ai_timeout: float
    ai_max_calls: int
    video_provider: str
    blockchain_rpc_url: str
    blockchain_private_key: str
    seed_demo_users: bool


def get_settings() -> Settings:
    data_dir = Path(os.getenv("VIVAD_DATA_DIR", VIVAD_ROOT / "data"))
    return Settings(
        data_dir=data_dir,
        db_path=data_dir / "vivad.db",
        upload_dir=data_dir / "uploads",
        report_dir=Path(os.getenv("VIVAD_REPORT_DIR", VIVAD_ROOT / "reports")),
        legal_dir=Path(os.getenv("VIVAD_LEGAL_DIR", VIVAD_ROOT / "data" / "legal")),
        max_upload_bytes=int(os.getenv("MAX_UPLOAD_MB", "50")) * 1024 * 1024,
        auth_secret=os.getenv("AUTH_SECRET", "vivad-demo-secret-do-not-use-in-production").strip(),
        session_hours=int(os.getenv("SESSION_HOURS", "12")),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip() or "gemini-2.0-flash",
        groq_api_key=os.getenv("GROQ_API_KEY", "").strip(),
        groq_model=os.getenv("GROQ_MODEL", "").strip() or "openai/gpt-oss-120b",
        ai_timeout=float(os.getenv("AI_TIMEOUT_SECONDS", "60")),
        ai_max_calls=int(os.getenv("AI_MAX_CALLS", "6")),
        video_provider=os.getenv("VIDEO_PROVIDER", "jitsi").strip() or "jitsi",
        blockchain_rpc_url=os.getenv("BLOCKCHAIN_RPC_URL", "").strip(),
        blockchain_private_key=os.getenv("BLOCKCHAIN_PRIVATE_KEY", "").strip(),
        seed_demo_users=os.getenv("VIVAD_SEED_DEMO_USERS", "1").strip() not in ("0", "false", "False"),
    )
