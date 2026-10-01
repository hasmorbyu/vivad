"""SQLite persistence for VIVAD.

Raw SQL, no ORM, mirroring the AMADEUS pattern: a single SCHEMA string executed by
init_db(), and a db() context manager that commits on success and rolls back on error.
The full domain model is created up-front so later phases do not migrate the schema.
"""
import sqlite3
from contextlib import contextmanager

from .config import get_settings

SCHEMA = """
-- ------------- identity & access
CREATE TABLE IF NOT EXISTS users(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  display_name TEXT, email TEXT,
  role TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT
);
CREATE TABLE IF NOT EXISTS sessions(
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL,
  created_at TEXT, expires_at TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions(user_id);

-- ------------- cases & intake
CREATE TABLE IF NOT EXISTS cases(
  id TEXT PRIMARY KEY,
  category TEXT, title TEXT NOT NULL, description TEXT,
  location TEXT, incident_date TEXT, amount REAL, currency TEXT DEFAULT 'INR',
  requested_resolution TEXT, urgency TEXT DEFAULT 'NORMAL',
  status TEXT NOT NULL DEFAULT 'INTAKE',
  priority TEXT DEFAULT 'NORMAL',
  current_stage TEXT DEFAULT 'INTAKE',
  next_action TEXT,
  created_by INTEGER, created_at TEXT, updated_at TEXT,
  synthetic INTEGER NOT NULL DEFAULT 0,
  summary_text TEXT, summary_source TEXT, summary_at TEXT,
  analysis_state TEXT NOT NULL DEFAULT 'NOT_RUN', analysis_at TEXT, analysis_json TEXT
);
CREATE TABLE IF NOT EXISTS parties(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL,
  contact TEXT, relationship TEXT, user_id INTEGER, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_parties_case ON parties(case_id);
CREATE TABLE IF NOT EXISTS statements(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, party_id INTEGER, kind TEXT DEFAULT 'INITIAL',
  what TEXT, when_text TEXT, where_text TEXT, who TEXT,
  claim TEXT, evidence_support TEXT, desired_resolution TEXT,
  submitted_by INTEGER, submitted_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_statements_case ON statements(case_id);

-- ------------- evidence & provenance
CREATE TABLE IF NOT EXISTS evidence(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, evidence_ref TEXT NOT NULL,
  filename TEXT, stored_path TEXT, source_type TEXT, media_type TEXT,
  file_size INTEGER, sha256 TEXT, uploader_id INTEGER, uploaded_at TEXT,
  description TEXT, related_party_id INTEGER, related_claim_id INTEGER,
  status TEXT, message TEXT,
  record_count INTEGER DEFAULT 0, line_count INTEGER DEFAULT 0,
  verify_status TEXT, verified_at TEXT, extracted_json TEXT,
  UNIQUE(case_id, evidence_ref)
);
CREATE INDEX IF NOT EXISTS ix_evidence_case ON evidence(case_id);
CREATE TABLE IF NOT EXISTS records(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, evidence_id INTEGER NOT NULL, ref TEXT NOT NULL,
  record_type TEXT, event_time TEXT, line_no INTEGER, line_end INTEGER,
  raw_text TEXT, normalized_json TEXT,
  UNIQUE(case_id, ref)
);
CREATE INDEX IF NOT EXISTS ix_records_case ON records(case_id);
CREATE INDEX IF NOT EXISTS ix_records_evidence ON records(evidence_id, line_no);

-- ------------- claims / issues / contradictions
CREATE TABLE IF NOT EXISTS claims(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, claim_ref TEXT NOT NULL, party_id INTEGER,
  text TEXT NOT NULL, date TEXT, amount REAL, status TEXT DEFAULT 'UNRESOLVED',
  source_statement_id INTEGER, extraction TEXT DEFAULT 'HUMAN',
  created_at TEXT, UNIQUE(case_id, claim_ref)
);
CREATE TABLE IF NOT EXISTS evidence_references(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, claim_id INTEGER, evidence_id INTEGER,
  relationship TEXT DEFAULT 'SUPPORTS', note TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_evref_claim ON evidence_references(claim_id);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, event_ref TEXT NOT NULL,
  event_time TEXT, time_precision TEXT DEFAULT 'second',
  title TEXT, description TEXT, event_type TEXT,
  evidence_id INTEGER, record_ref TEXT, origin TEXT DEFAULT 'EVIDENCE',
  created_at TEXT, UNIQUE(case_id, event_ref)
);
CREATE TABLE IF NOT EXISTS issues(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, issue_ref TEXT NOT NULL,
  title TEXT, description TEXT, status TEXT DEFAULT 'OPEN', created_at TEXT,
  UNIQUE(case_id, issue_ref)
);
CREATE TABLE IF NOT EXISTS contradictions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, contradiction_ref TEXT NOT NULL,
  kind TEXT NOT NULL, title TEXT,
  claim_a_id INTEGER, claim_b_id INTEGER,
  evidence_ids TEXT, explanation TEXT, confidence TEXT,
  origin TEXT DEFAULT 'DETERMINISTIC',
  verification_status TEXT DEFAULT 'REQUIRES_HUMAN_REVIEW',
  reviewed_by INTEGER, reviewed_at TEXT, created_at TEXT,
  UNIQUE(case_id, contradiction_ref)
);

-- ------------- legal references
CREATE TABLE IF NOT EXISTS legal_references(
  id TEXT PRIMARY KEY, jurisdiction TEXT, act TEXT, section TEXT,
  title TEXT, description TEXT, source_url TEXT, last_verified TEXT,
  concepts TEXT, disclaimer TEXT
);
CREATE TABLE IF NOT EXISTS case_legal_refs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, legal_reference_id TEXT NOT NULL,
  relevance TEXT, concepts TEXT, origin TEXT DEFAULT 'DETERMINISTIC',
  status TEXT DEFAULT 'POTENTIALLY_RELEVANT', created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_caselaw_case ON case_legal_refs(case_id);

-- ------------- hearings & meetings
CREATE TABLE IF NOT EXISTS hearings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, scheduled_at TEXT, duration_min INTEGER DEFAULT 30,
  status TEXT NOT NULL DEFAULT 'SCHEDULED', agenda TEXT,
  provider TEXT, room_id TEXT,
  created_by INTEGER, created_at TEXT, completed_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_hearings_case ON hearings(case_id);
CREATE TABLE IF NOT EXISTS hearing_participants(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hearing_id INTEGER NOT NULL, user_id INTEGER, party_id INTEGER,
  name TEXT, role TEXT, invited INTEGER DEFAULT 1, attended INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS hearing_notes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hearing_id INTEGER NOT NULL, author_id INTEGER, body_json TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS meeting_sessions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  hearing_id INTEGER NOT NULL, provider TEXT, room_id TEXT,
  status TEXT DEFAULT 'READY', started_at TEXT, ended_at TEXT,
  recording INTEGER DEFAULT 0, consent INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS meeting_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER, user_id INTEGER, event TEXT, detail TEXT, created_at TEXT
);

-- ------------- evidence requests (human asks a party for more material)
CREATE TABLE IF NOT EXISTS evidence_requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, about TEXT, note TEXT, party_id INTEGER,
  requested_by INTEGER, status TEXT DEFAULT 'OPEN', created_at TEXT, resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_evreq_case ON evidence_requests(case_id);

-- ------------- AI & human review
CREATE TABLE IF NOT EXISTS ai_analyses(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, provider TEXT, model TEXT, prompt_version TEXT,
  status TEXT, input_json TEXT, output_json TEXT, validation TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_aian_case ON ai_analyses(case_id);
CREATE TABLE IF NOT EXISTS ai_findings(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, finding_ref TEXT NOT NULL, analysis_id INTEGER,
  kind TEXT, title TEXT, body TEXT, evidence_ids TEXT, claim_ids TEXT,
  confidence TEXT, validation TEXT, origin TEXT DEFAULT 'AI',
  human_status TEXT DEFAULT 'PENDING', reviewer_id INTEGER, reviewed_at TEXT,
  created_at TEXT, UNIQUE(case_id, finding_ref)
);
CREATE TABLE IF NOT EXISTS human_reviews(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, finding_id INTEGER, action TEXT,
  edited_body TEXT, comment TEXT, reviewer_id INTEGER, created_at TEXT
);
CREATE TABLE IF NOT EXISTS decisions(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT NOT NULL, decision_ref TEXT NOT NULL, status TEXT,
  decision TEXT, reason TEXT,
  evidence_ids TEXT, legal_refs TEXT,
  accepted_finding_ids TEXT, rejected_finding_ids TEXT,
  observations TEXT, decided_by INTEGER, decided_at TEXT,
  human_validated INTEGER NOT NULL DEFAULT 1,
  UNIQUE(case_id, decision_ref)
);

-- ------------- audit & integrity
CREATE TABLE IF NOT EXISTS audit_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seq INTEGER, case_id TEXT, actor_id INTEGER, actor_role TEXT,
  action TEXT NOT NULL, object_type TEXT, object_id TEXT,
  prev_state TEXT, new_state TEXT, detail TEXT,
  created_at TEXT, prev_hash TEXT, record_hash TEXT
);
CREATE INDEX IF NOT EXISTS ix_audit_case ON audit_events(case_id, seq);
CREATE TABLE IF NOT EXISTS integrity_records(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  seq INTEGER, case_id TEXT, kind TEXT,
  object_type TEXT, object_id TEXT, object_hash TEXT,
  prev_hash TEXT, record_hash TEXT,
  anchor_status TEXT DEFAULT 'LOCAL_ONLY', anchor_ref TEXT,
  created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_integrity_case ON integrity_records(case_id, seq);

-- ------------- notifications
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  case_id TEXT, user_id INTEGER, kind TEXT, title TEXT, body TEXT,
  read INTEGER NOT NULL DEFAULT 0, created_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_notif_user ON notifications(user_id, read);

-- ------------- counters for human-readable refs (E-001, CL-001, ...)
CREATE TABLE IF NOT EXISTS counters(
  name TEXT PRIMARY KEY, value INTEGER NOT NULL DEFAULT 0
);
"""


def connect() -> sqlite3.Connection:
    s = get_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(s.db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = connect()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def db():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
