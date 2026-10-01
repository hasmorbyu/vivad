"""Plain monochrome PDF report (ReportLab). AI-assisted and human-validated material is labelled."""
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .serialize import build_report


def _register_fonts():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for reg, bold in [("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"),
                      ("/usr/share/fonts/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf")]:
        try:
            pdfmetrics.registerFont(TTFont("VivMono", reg))
            pdfmetrics.registerFont(TTFont("VivMono-Bold", bold))
            return "VivMono", "VivMono-Bold", True
        except Exception:  # noqa: BLE001
            continue
    return "Courier", "Courier-Bold", False


FONT, FONT_B, UNICODE = _register_fonts()
S = {
    "h1": ParagraphStyle("h1", fontName=FONT_B, fontSize=15, leading=18, spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName=FONT_B, fontSize=10.5, leading=13, spaceBefore=12, spaceAfter=4),
    "b": ParagraphStyle("b", fontName=FONT, fontSize=8, leading=10.5),
    "s": ParagraphStyle("s", fontName=FONT, fontSize=6.8, leading=8.4),
    "sb": ParagraphStyle("sb", fontName=FONT_B, fontSize=6.8, leading=8.4),
}
_ASCII = {"[✓]": "[v]", "[■]": "[#]", "[□]": "[ ]", "₹": "INR ", "→": "->", "↔": "<->", "…": "...", "·": "-", "—": "-", "–": "-"}


def _clean(t) -> str:
    t = str(t)
    if UNICODE:
        return t
    for k, v in _ASCII.items():
        t = t.replace(k, v)
    return t.encode("latin-1", "replace").decode("latin-1")


def P(t, st="b"):
    return Paragraph(escape(_clean(t)).replace("\n", "<br/>"), S[st])


def _table(rows, widths, header=True):
    t = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, colors.black), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E5E5")))
    t.setStyle(TableStyle(st))
    return t


def build_pdf(conn, case_id: str) -> bytes:
    r = build_report(conn, case_id)
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=14 * mm, bottomMargin=16 * mm,
                            title=f"VIVAD {case_id}", author="VIVAD")
    W = 180 * mm
    el = [P("VIVAD CASE REPORT", "h1"), P("Verified Intake & Validation for Assisted Dispute-resolution", "b"),
          P("AI assists analysis. Humans make the final decision.", "sb"), Spacer(1, 3),
          P(f"CASE {r['case']['id']} · GENERATED {r['generated_at']}", "s"), P(r["disclaimer"], "s")]

    el.append(P("1. CASE OVERVIEW", "h2"))
    c = r["1_case_overview"]
    el.append(_table([[P(k, "sb"), P(v, "s")] for k, v in [
        ("CATEGORY", c["category"]), ("STATUS", c["status"]), ("STAGE", c["stage"]),
        ("AMOUNT", f"{c['currency']} {c['amount']:,.2f}" if c["amount"] else "-"), ("LOCATION", c["location"] or "-"),
        ("DESCRIPTION", c["description"] or "-"), ("REQUESTED RESOLUTION", c["requested_resolution"] or "-"),
        ("CASE SUMMARY", c["summary"] or "Not generated."), ("SUMMARY SOURCE", c["summary_source"] or "-")]],
        [45 * mm, W - 45 * mm], header=False))

    el.append(P("2. PARTY STATEMENTS", "h2"))
    rows = [[P(h, "sb") for h in ("PARTY", "TYPE", "CLAIM", "WHEN")]]
    for s in r["2_party_statements"]["statements"]:
        rows.append([P(s["party_name"] or "-", "s"), P(s["kind"], "s"), P(s["claim"] or s["what"] or "-", "s"), P(s["when_text"] or "-", "s")])
    el.append(_table(rows, [30 * mm, 22 * mm, 108 * mm, 20 * mm]))

    el.append(P("3. ISSUES IDENTIFIED (CLAIMS AND CONTRADICTIONS)", "h2"))
    rows = [[P(h, "sb") for h in ("CLAIM", "PARTY-AGNOSTIC TEXT", "STATUS", "SUPPORT")]]
    for cl in r["3_issues_identified"]["claims"]:
        rows.append([P(cl["claim_ref"], "s"), P(cl["text"], "s"), P(cl["status"], "s"), P(", ".join(cl["evidence"]) or "-", "s")])
    el.append(_table(rows, [16 * mm, 96 * mm, 30 * mm, 38 * mm]))

    el.append(P("4. EVIDENCE (WITH SHA-256)", "h2"))
    rows = [[P(h, "sb") for h in ("REF", "FILE", "TYPE", "SHA-256 (FULL)", "INTEGRITY")]]
    for e in r["4_evidence"]:
        rows.append([P(e["evidence_ref"], "s"), P(e["filename"], "s"), P(e["source_type"], "s"), P(e["sha256"], "s"), P(e["verify_status"] or "NOT CHECKED", "s")])
    el.append(_table(rows, [14 * mm, 44 * mm, 22 * mm, 76 * mm, 24 * mm]))
    el.append(P("SHA-256 verifies file integrity and detects change. It does not by itself establish chain of custody.", "s"))

    el.append(P("5. EVIDENCE-CLAIM RELATIONSHIPS", "h2"))
    rows = [[P(h, "sb") for h in ("CLAIM", "EVIDENCE")]]
    for rel in r["5_evidence_claim_relationships"]:
        rows.append([P(rel["claim"], "s"), P(", ".join(rel["evidence"]) or "none linked", "s")])
    el.append(_table(rows, [30 * mm, 150 * mm]))

    el.append(P("6. POTENTIAL CONTRADICTIONS", "h2"))
    for x in r["6_potential_contradictions"]:
        el.append(KeepTogether([P(f"{x['contradiction_ref']}  {x['kind']}  ({x['verification_status']})", "sb"),
                                P(x["title"], "b"), P(x["explanation"], "s"),
                                P(f"BASIS: {x['confidence'] or '-'} · HUMAN STATUS: {x['verification_status']}", "s"), Spacer(1, 5)]))
    if not r["6_potential_contradictions"]:
        el.append(P("None detected.", "b"))

    el.append(P("7. RELEVANT LEGAL REFERENCES (REFERENCE MATERIAL ONLY)", "h2"))
    rows = [[P(h, "sb") for h in ("ACT", "SECTION", "TITLE", "SOURCE")]]
    for l in r["7_legal_references"]:
        rows.append([P(l["act"], "s"), P(l["section"], "s"), P(l["title"], "s"), P(l["source_url"], "s")])
    el.append(_table(rows, [46 * mm, 16 * mm, 62 * mm, 56 * mm]))
    el.append(P("Provided for reference. VIVAD does not interpret the law or determine liability. Verify against the official source.", "s"))

    el.append(P("8. HEARING HISTORY", "h2"))
    for h in r["8_hearing_history"]:
        el.append(P(f"{h['scheduled_at'] or 'unscheduled'} · {h['status']} · {h['agenda'] or ''}", "sb"))
        el.append(P("Participants: " + ", ".join(f"{p['name']} ({p['role']}){' [attended]' if p['attended'] else ''}" for p in h["participants"]), "s"))
        for n in h["notes"]:
            el.append(P("Note " + n["created_at"] + ": " + " | ".join(f"{k}={v}" for k, v in n["body"].items() if v), "s"))
    if not r["8_hearing_history"]:
        el.append(P("No hearings recorded.", "b"))

    el.append(P("9. AI-ASSISTED ANALYSIS", "h2"))
    for f in r["9_ai_assisted_analysis"]["findings"]:
        el.append(P(f"{f['finding_ref']} [{f['origin']}] {f['title']} — {f['body']}", "s"))
    el.append(P("AI-assisted material only. It is not a decision and must be validated by a human.", "s"))

    el.append(P("10. HUMAN REVIEW", "h2"))
    rows = [[P(h, "sb") for h in ("ACTION", "REVIEWER", "WHEN", "COMMENT")]]
    for rv in r["10_human_review"]["reviews"]:
        rows.append([P(rv["action"], "s"), P(f"{rv['reviewer'] or '-'} ({rv['reviewer_role'] or '-'})", "s"), P(rv["created_at"], "s"), P(rv["comment"] or "-", "s")])
    el.append(_table(rows, [30 * mm, 48 * mm, 40 * mm, 62 * mm]))

    el.append(P("11. HUMAN DECISION / PRELIMINARY RESOLUTION", "h2"))
    d = r["11_human_decision"]
    if d:
        el.append(_table([[P(k, "sb"), P(v, "s")] for k, v in [
            ("DECISION", d["decision"]), ("STATUS", d["status"]), ("REASON", d["reason"]),
            ("EVIDENCE CONSIDERED", ", ".join(d["evidence_ids"]) or "-"),
            ("LEGAL REFERENCES CONSULTED", ", ".join(d["legal_refs"]) or "-"),
            ("AI FINDINGS ACCEPTED", ", ".join(d["accepted_finding_ids"]) or "-"),
            ("AI FINDINGS REJECTED", ", ".join(d["rejected_finding_ids"]) or "-"),
            ("OBSERVATIONS", d["observations"] or "-"),
            ("DECISION MAKER", f"user {d['decided_by']}"), ("DECIDED AT", d["decided_at"]),
        ]], [50 * mm, W - 50 * mm], header=False))
    else:
        el.append(P("No human decision has been recorded. This case is not resolved.", "b"))

    el.append(P("12. AUDIT INFORMATION", "h2"))
    chain = r["12_audit_information"]["audit_chain"]
    el.append(P(f"Audit chain: {'OK' if chain['ok'] else 'WARNING at event ' + str(chain.get('broken_at'))} ({chain.get('events', 0)} events).", "s"))
    rows = [[P(h, "sb") for h in ("SEQ", "ACTION", "ROLE", "OBJECT", "WHEN")]]
    for ev in r["12_audit_information"]["events"][:120]:
        rows.append([P(ev["seq"], "s"), P(ev["action"], "s"), P(ev["actor_role"], "s"), P(f"{ev['object_type']}:{ev['object_id']}", "s"), P(ev["created_at"], "s")])
    el.append(_table(rows, [12 * mm, 50 * mm, 22 * mm, 40 * mm, 56 * mm]))
    el.append(P("Every evidence file's SHA-256 is listed in section 4. Hash chains are tamper-evident, not proof of authorship or custody.", "s"))

    doc.build(el)
    return buf.getvalue()
