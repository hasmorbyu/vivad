# VIVAD

**Verified Intake & Validation for Assisted Dispute-resolution**

An AI-assisted, human-controlled preliminary dispute-resolution platform for minor and
low-severity disputes. VIVAD is a sibling product to AMADEUS and lives entirely inside
`amadeus/vivad/`; the AMADEUS application is untouched.

> **AI assists analysis. Humans make the final decision.**

## What VIVAD is (and is not)

VIVAD **is** a structured dispute-intake and evidence-organisation system, an AI-assisted
analysis and contradiction-detection aid, an explainable case-review workspace, a
hearing/scheduling interface, and an auditable evidence-and-decision record.

VIVAD is **not** an autonomous judge, an AI lawyer, a guilt determiner, an automated court,
or a system that issues legally binding judgments. Every AI-generated assertion is labelled,
grounded in evidence, schema-validated, and subject to a recorded human action. No AI output
becomes a decision without a human.

## Architecture

```
backend/app/
  main.py, config.py, db.py            FastAPI app, settings, SQLite schema
  auth.py, seed.py                     PBKDF2 auth, sessions, server-side RBAC
  audit.py, ledger.py, integrity.py    append-only hash-chained audit + SHA-256
  anchor.py, notify.py, refs.py         anchoring adapter, notifications, E-/CL-/EV- refs
  ingest.py, nlp.py, parsers/          safe upload, SHA-256, parsing, deterministic extraction
  intel/                               claims, timeline, contradictions, legal association
  ai/                                  provider abstraction (Gemini→Groq), schemas, grounded service
  graph/builder.py                     NetworkX → Cytoscape case graph
  analysis.py                          step-by-step orchestration (background, pollable)
  reports/                             JSON serialiser + ReportLab PDF (12 sections)
  api/                                 auth, cases, parties, statements, evidence, intel,
                                       graph, reviews, hearings, decisions, notifications,
                                       search, reports, meta, health
frontend/src/                          React + Vite + TS + Tailwind v4 + react-router
  components/                          Shell, CaseLayout, ui, EvidenceRef
  pages/                               Login, Dashboard, Cases, NewCase, Search, Notifications,
                                       HearingRoom, and case/* (Overview, Parties, Statements,
                                       Evidence, Timeline, Claims, Contradictions, Legal, Graph,
                                       Review, Decision, Audit, Report)
data/legal/india.json                  curated, source-attributed legal reference dataset
scripts/generate_demo.py               seeds synthetic case VV-2026-00042 end to end
tests/                                 pytest (auth, intake, intelligence, graph, workflow,
                                       integrity/report, search, AI validation)
```

## Pipeline

```
upload → SHA-256 → parse → deterministic extraction → claims → evidence links → timeline
→ contradictions → legal association → AI-assisted analysis (optional, grounded)
→ findings → human review → hearing → human decision → audit + report
```

Deterministic code owns identifiers, permissions, timestamps, hashes, status transitions and
the decision record. AI only summarises and suggests; its output is validated against a
schema and its evidence IDs checked against the case.

## Roles

`CITIZEN`/`COMPLAINANT`, `RESPONDENT`, `CASE_OFFICER`, `REVIEWER`, `CHAIR`, `ADMIN`.
Authorization is enforced server-side; a user only sees cases they created or are a party to
unless they hold a staff role.

## Setup

VIVAD uses its own virtual environment (the repository-root `.venv` was created for an older
Python and is not used here).

```bash
# from the repository root
uv venv vivad/.venv --python 3.12
uv pip install -r vivad/backend/requirements.txt --python vivad/.venv/bin/python

# frontend
npm --prefix vivad/frontend install
```

Optional `.env` (root or exported): `GEMINI_API_KEY` (preferred), `GROQ_API_KEY` (fallback),
`VIDEO_PROVIDER` (`jitsi` default, or `local`), `AUTH_SECRET`. With no AI key VIVAD runs
deterministically and shows **AI UNAVAILABLE**.

## Running

```bash
# terminal 1 — API on :8001
cd vivad/backend && ../.venv/bin/uvicorn app.main:app --reload --port 8001

# terminal 2 — UI on :5174 (proxies /api → :8001)
npm --prefix vivad/frontend run dev
```

Open http://localhost:5174 and sign in. Demo accounts (password `vivad123`):
`citizen`, `respondent`, `officer`, `reviewer`, `chair`, `admin`. Or click **VIEW DEMO CASE**.

## Demo case

```bash
vivad/.venv/bin/python vivad/scripts/generate_demo.py
```

Seeds **VV-2026-00042**, a fully synthetic rental security-deposit dispute (₹40,000 paid;
₹15,000 deduction claimed): parties, statements, six evidence files, analysis, two potential
contradictions, legal references, human review, a completed hearing with notes, and a human
preliminary resolution. All names, accounts and amounts are fictional.

## Testing

```bash
vivad/.venv/bin/python -m pytest vivad/tests -q      # backend
npm --prefix vivad/frontend run build                 # typecheck + build
npm --prefix vivad/frontend run lint                  # oxlint
```

## Epistemic and safety constraints

- AI never creates identifiers, correlations, graph edges, contradictions, decisions or
  final findings; those are deterministic or human.
- AI output is schema-validated and grounded: evidence IDs not present in the case are
  dropped, and no AI output becomes a decision without a recorded human action.
- Uploaded documents are untrusted content. Instructions inside evidence are treated as
  data and never executed; prompt-injection text is contained by the system prompt and the
  validation layer.
- The system never labels a party guilty, dishonest or liable, and always exposes
  uncertainty.
- SHA-256 verifies integrity and detects change; it does not establish chain of custody or
  authorship. Only hashes would ever be eligible for external anchoring, never case data.
- Legal references are curated, source-attributed reference material. VIVAD does not
  interpret the law or give legal advice. No provision, section or citation is fabricated;
  an unavailable reference is marked as such.
