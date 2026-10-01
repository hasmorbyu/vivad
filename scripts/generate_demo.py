#!/usr/bin/env python3
"""Seed the fully synthetic demonstration case VV-2026-00042 into VIVAD.

Everything here is fictional. The script builds a rental / security-deposit dispute end to
end: parties, statements, evidence files, analysis, human review, a hearing and a human
decision — so the product can be demonstrated without any manual database work.

Run from the repository root:
    vivad/.venv/bin/python vivad/scripts/generate_demo.py
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "vivad" / "backend"))

from app import analysis, audit  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.db import db, init_db  # noqa: E402
from app.ingest import ingest_evidence, store_upload  # noqa: E402
from app.integrity import canonical_json, sha256_text  # noqa: E402
from app.ledger import append_integrity, now_iso  # noqa: E402
from app.meetings import room_for  # noqa: E402
from app.seed import seed_demo_users  # noqa: E402

CASE_ID = "VV-2026-00042"

AGREEMENT = """RENTAL AGREEMENT NO. RA-2026-0042
Landlord: Neel Kapoor
Tenant: Aarav Menon
Property: 12 Rose Apartments, Bengaluru
Monthly rent: Rs. 20,000
Security deposit: Rs. 40,000 paid on 2026-09-14
Lease period: 12 months from 2026-09-14
The security deposit is refundable on vacating, less any agreed damage.
"""

PAYMENTS = """payment_id,payment_date,payer,payee,amount,status,reference
P-1001,2026-09-14,Aarav Menon,Neel Kapoor,40000,SUCCESS,UPI/RA-2026-0042/626214321877
"""

MESSAGES = """14/09/2026, 18:05 - Aarav: I have paid the security deposit of Rs. 40,000 as agreed.
14/09/2026, 18:11 - Neel: Received, thank you.
20/09/2026, 10:20 - Neel: I inspected the flat today. There is damage to the kitchen wall.
20/09/2026, 10:22 - Aarav: Please share the repair estimate before deducting anything.
25/09/2026, 09:40 - Neel: I will only return part of the deposit after the repair cost.
25/09/2026, 09:45 - Aarav: I did not agree to that deduction.
"""

INSPECTION = """INSPECTION NOTE
Date: 2026-09-20
Property: 12 Rose Apartments, Bengaluru
Observed: scuff marks and a hairline crack on the kitchen wall, behind the counter.
The note does not attribute a cause and does not state a repair cost.
"""

INVOICE = """REPAIR INVOICE INV-2026-118
Date: 2026-09-22
Property: 12 Rose Apartments, Bengaluru
Work: replaster and repaint kitchen wall
Amount: Rs. 15,000
Issued by: Sunrise Interiors
This invoice has not been linked to the inspection note by an independent assessment.
"""

EMAIL = """From: Aarav Menon <aarav.menon@mailbox.example>
To: Neel Kapoor <neel.kapoor@mailbox.example>
Subject: Security deposit of Rs. 40,000
Date: Fri, 25 Sep 2026 10:05:00 +0530

I have asked for the repair estimate before any deduction from the Rs. 40,000 deposit.
Please return the deposit in full unless a cost is agreed.
"""

EVIDENCE_FILES = [
    ("rental_agreement.txt", AGREEMENT),
    ("payment_record.csv", PAYMENTS),
    ("messages.txt", MESSAGES),
    ("inspection_note.txt", INSPECTION),
    ("repair_invoice.txt", INVOICE),
    ("deposit_dispute_email.eml", EMAIL),
]


def _user_id(conn, username):
    row = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    return row["id"] if row else None


def _exists(conn):
    return conn.execute("SELECT 1 FROM cases WHERE id=?", (CASE_ID,)).fetchone() is not None


def build_case():
    init_db()
    seed_demo_users()
    with db() as c:
        if _exists(c):
            print(f"{CASE_ID} already exists — nothing to do.")
            return
        citizen = _user_id(c, "citizen")
        respondent = _user_id(c, "respondent")
        officer = _user_id(c, "officer")

        c.execute(
            "INSERT INTO cases(id, category, title, description, location, incident_date, amount, currency,"
            " requested_resolution, urgency, priority, status, current_stage, next_action, created_by, created_at, updated_at, synthetic)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (CASE_ID, "RENTAL_DISPUTE", "Security deposit deduction dispute",
             "Tenant seeks return of a ₹40,000 security deposit; landlord proposes a deduction for alleged damage.",
             "Bengaluru", "2026-09-14", 40000, "INR",
             "Return of the security deposit, less any cost agreed by both parties.",
             "NORMAL", "HIGH", "PROCESSING", "EVIDENCE", "Run analysis", officer, now_iso(), now_iso()))
        c.execute("INSERT INTO parties(case_id, name, role, contact, relationship, user_id, created_at) VALUES(?,?,?,?,?,?,?)",
                  (CASE_ID, "Aarav Menon", "COMPLAINANT", "+91 98765 43210", "Tenant", citizen, now_iso()))
        a_id = c.execute("SELECT id FROM parties WHERE case_id=? AND role='COMPLAINANT'", (CASE_ID,)).fetchone()["id"]
        c.execute("INSERT INTO parties(case_id, name, role, contact, relationship, user_id, created_at) VALUES(?,?,?,?,?,?,?)",
                  (CASE_ID, "Neel Kapoor", "RESPONDENT", "+91 90000 11111", "Landlord", respondent, now_iso()))
        b_id = c.execute("SELECT id FROM parties WHERE case_id=? AND role='RESPONDENT'", (CASE_ID,)).fetchone()["id"]

        c.execute(
            "INSERT INTO statements(case_id, party_id, kind, what, when_text, where_text, who, claim, evidence_support, desired_resolution, submitted_by, submitted_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (CASE_ID, a_id, "INITIAL", "Paid the full security deposit by UPI when the lease began.",
             "14 Sep 2026", "12 Rose Apartments, Bengaluru", "Aarav Menon and Neel Kapoor",
             "The full Rs. 40,000 security deposit was paid on 14 Sep 2026.",
             "Bank/UPI payment record and the rental agreement.", "Return the deposit in full.", citizen, now_iso()))
        c.execute(
            "INSERT INTO statements(case_id, party_id, kind, what, when_text, where_text, who, claim, evidence_support, desired_resolution, submitted_by, submitted_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (CASE_ID, b_id, "RESPONSE", "States that less was received and that a deduction is owed for damage.",
             "14 Sep 2026", "12 Rose Apartments, Bengaluru", "Aarav Menon and Neel Kapoor",
             "Only Rs. 25,000 was paid towards the deposit and Rs. 15,000 is deductible for damage.",
             "Repair invoice INV-2026-118.", "Set off the repair cost against the deposit.", respondent, now_iso()))
        audit.record(c, {"id": officer, "role": "CASE_OFFICER"}, "CASE_CREATED", case_id=CASE_ID,
                     object_type="case", object_id=CASE_ID, new_state="INTAKE", detail="synthetic demonstration case")
        print(f"created {CASE_ID} with parties and statements")

    # write and ingest evidence
    demo_dir = Path(get_settings().data_dir) / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    ids = []
    for name, content in EVIDENCE_FILES:
        path = demo_dir / name
        path.write_text(content)
        with open(path, "rb") as fh:
            rec = store_upload(CASE_ID, name, fh, uploader_id=citizen, description="Synthetic demonstration evidence")
        ingest_evidence(rec["id"])
        ids.append(rec["evidence_ref"])
    print(f"ingested evidence: {', '.join(ids)}")

    # analysis (thread + poll)
    analysis.start_analysis(CASE_ID, {"id": officer, "role": "CASE_OFFICER"})
    deadline = time.time() + 120
    while time.time() < deadline:
        state = analysis.get_status(CASE_ID)["state"]
        if state != "RUNNING":
            break
        time.sleep(0.5)
    print(f"analysis: {state}")

    _human_review(citizen, officer)
    _hearing(officer, a_id, b_id, citizen, respondent)
    _decision(officer)
    print("demo case ready: open /cases/VV-2026-00042")


def _human_review(citizen, officer):
    actor = {"id": officer, "role": "CASE_OFFICER"}
    with db() as c:
        findings = [dict(r) for r in c.execute("SELECT * FROM ai_findings WHERE case_id=? ORDER BY finding_ref", (CASE_ID,))]
        accepted = rejected = 0
        for f in findings:
            if f["kind"] in ("FACT_SUPPORTED", "RESOLUTION_PATH"):
                action = "ACCEPT"
                accepted += 1
            elif f["kind"] in ("CLAIM_REQUIRING_VERIFICATION", "MISSING_INFORMATION"):
                action = "MARK_UNRESOLVED"
                rejected += 1
            else:
                continue
            c.execute("UPDATE ai_findings SET human_status=?, reviewer_id=?, reviewed_at=? WHERE id=?",
                      (action, officer, now_iso(), f["id"]))
            c.execute("INSERT INTO human_reviews(case_id, finding_id, action, edited_body, comment, reviewer_id, created_at) VALUES(?,?,?,?,?,?,?)",
                      (CASE_ID, f["id"], action, None, "Reviewed against the supplied evidence.", officer, now_iso()))
            audit.record(c, actor, "FINDING_ACCEPTED" if action == "ACCEPT" else "FINDING_MARKED_UNRESOLVED",
                         case_id=CASE_ID, object_type="ai_finding", object_id=f["finding_ref"], new_state=action)
        print(f"human review: {accepted} accepted, {rejected} marked unresolved")


def _hearing(officer, a_id, b_id, citizen, respondent):
    actor = {"id": officer, "role": "CASE_OFFICER"}
    when = "2026-10-03T11:30:00+05:30"
    with db() as c:
        room = room_for(CASE_ID, 1)
        cur = c.execute(
            "INSERT INTO hearings(case_id, scheduled_at, duration_min, status, agenda, provider, room_id, created_by, created_at)"
            " VALUES(?,?,?,?,?,?,?,?,?)",
            (CASE_ID, when, 30, "COMPLETED", "Review the disputed security-deposit deduction.", room.provider, room.room_id, officer, now_iso()))
        hid = cur.lastrowid
        c.execute("UPDATE hearings SET room_id=? WHERE id=?", (room_for(CASE_ID, hid).room_id, hid))
        for uid, pid, name, role in [(citizen, a_id, "Aarav Menon", "COMPLAINANT"), (respondent, b_id, "Neel Kapoor", "RESPONDENT"),
                                     (officer, None, "Case Officer 17", "CASE_OFFICER")]:
            c.execute("INSERT INTO hearing_participants(hearing_id, user_id, party_id, name, role, invited, attended) VALUES(?,?,?,?,?,1,1)",
                      (hid, uid, pid, name, role))
        note = {"issue": "Whether Rs. 15,000 may be deducted for the alleged kitchen-wall damage.",
                "party_a": "Aarav Menon states the full Rs. 40,000 deposit was paid on 14 Sep 2026.",
                "party_b": "Neel Kapoor states Rs. 15,000 should be deducted for repairs.",
                "additional_evidence": "Neither party produced an independent assessment linking the invoice to pre-existing damage.",
                "next_action": "Record a preliminary resolution and note that the deduction is not yet agreed."}
        c.execute("INSERT INTO hearing_notes(hearing_id, author_id, body_json, created_at) VALUES(?,?,?,?)",
                  (hid, officer, json.dumps(note), now_iso()))
        c.execute("UPDATE hearing_participants SET attended=1 WHERE hearing_id=?", (hid,))
        c.execute("UPDATE cases SET status='AWAITING_DECISION', current_stage='DECISION', next_action='Human decision required', updated_at=? WHERE id=?",
                  (now_iso(), CASE_ID))
        audit.record(c, actor, "HEARING_SCHEDULED", case_id=CASE_ID, object_type="hearing", object_id=hid, new_state="SCHEDULED", detail=when)
        audit.record(c, actor, "HEARING_COMPLETED", case_id=CASE_ID, object_type="hearing", object_id=hid, new_state="COMPLETED")
        print("hearing scheduled, held and completed with notes")


def _decision(officer):
    actor = {"id": officer, "role": "CHAIR"}
    body = {
        "status": "PRELIMINARY_RESOLUTION_ACCEPTED",
        "decision": "The Rs. 40,000 security deposit was paid and is to be returned to the tenant, less any deduction only if the parties agree to it.",
        "reason": "The payment record and the agreement both support that Rs. 40,000 was paid. The claimed Rs. 15,000 deduction rests on an invoice that has not been independently linked to damage caused by the tenant, and the tenant did not agree to it.",
        "evidence_ids": ["E-001", "E-002", "E-003", "E-005"],
        "legal_refs": ["IN-CONTRACT-1872-S73", "IN-TPA-1882-S108"],
        "observations": "Recorded as a preliminary, non-binding resolution. Either party may escalate.",
    }
    with db() as c:
        accepted = [r["finding_ref"] for r in c.execute("SELECT finding_ref FROM ai_findings WHERE case_id=? AND human_status IN ('ACCEPT','EDIT')", (CASE_ID,))]
        rejected = [r["finding_ref"] for r in c.execute("SELECT finding_ref FROM ai_findings WHERE case_id=? AND human_status IN ('REJECT','MARK_UNRESOLVED')", (CASE_ID,))]
        ref = "D-001"
        payload = {"decision_ref": ref, **body, "accepted": accepted, "rejected": rejected, "decided_by": officer, "decided_at": now_iso()}
        c.execute(
            "INSERT INTO decisions(case_id, decision_ref, status, decision, reason, evidence_ids, legal_refs, accepted_finding_ids,"
            " rejected_finding_ids, observations, decided_by, decided_at, human_validated) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)",
            (CASE_ID, ref, body["status"], body["decision"], body["reason"], json.dumps(body["evidence_ids"]),
             json.dumps(body["legal_refs"]), json.dumps(accepted), json.dumps(rejected), body["observations"], officer, now_iso()))
        append_integrity(c, case_id=CASE_ID, kind="DECISION", object_type="decision", object_id=ref,
                         object_hash=sha256_text(canonical_json(payload)))
        c.execute("UPDATE cases SET status='RESOLVED', current_stage='CLOSED', next_action='Case closed', updated_at=? WHERE id=?",
                  (now_iso(), CASE_ID))
        audit.record(c, actor, "DECISION_RECORDED", case_id=CASE_ID, object_type="decision", object_id=ref,
                     new_state=body["status"], detail=body["decision"][:200])
        print("human decision recorded")


if __name__ == "__main__":
    build_case()
