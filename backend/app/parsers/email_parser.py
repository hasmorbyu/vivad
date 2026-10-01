"""Email (.eml) and mbox parsing."""
import re
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses
from pathlib import Path

from .common import ParseError, ParsedRecord, ParseResult, parse_time, read_text

MBOX_SEP = re.compile(r"^From \S+.*\d{4}\s*$")


def parse(path: Path, filename: str) -> ParseResult:
    text = read_text(path)
    if not text.strip():
        raise ParseError("EMPTY FILE")
    lines = text.splitlines()
    starts = [i for i, l in enumerate(lines) if MBOX_SEP.match(l)]
    chunks = []
    if starts:
        bounds = starts + [len(lines)]
        for a, b in zip(bounds, bounds[1:]):
            chunks.append((a + 2, b, "\n".join(lines[a + 1:b])))
    else:
        chunks.append((1, len(lines), text))
    recs, warns = [], []
    for start, end, chunk in chunks:
        try:
            msg = BytesParser(policy=policy.default).parsebytes(chunk.encode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            warns.append(f"message at line {start} unparseable: {e}")
            continue
        if not (msg["From"] or msg["Message-ID"] or msg["Subject"]):
            warns.append(f"message at line {start} has no recognisable headers")
            continue
        recs.append(_record(msg, chunk, start, end))
    if not recs:
        raise ParseError("NO PARSEABLE EMAIL MESSAGES")
    return ParseResult("EMAIL", recs, len(lines), warns)


def _addrs(msg, h):
    return [(n.strip(), a.strip()) for n, a in getaddresses([str(x) for x in msg.get_all(h, [])]) if a]


def _record(msg, chunk, start, end) -> ParsedRecord:
    when, prec = parse_time(str(msg["Date"] or ""))
    frm, to, cc = _addrs(msg, "From"), _addrs(msg, "To"), _addrs(msg, "Cc")
    body_part = msg.get_body(preferencelist=("plain", "html"))
    try:
        body = body_part.get_content() if body_part else ""
    except Exception:  # noqa: BLE001
        body = ""
    atts = [p.get_filename() for p in msg.iter_attachments() if p.get_filename()]
    f = {
        "from": str(msg["From"] or ""), "to": str(msg["To"] or ""), "cc": str(msg["Cc"] or ""),
        "subject": str(msg["Subject"] or ""), "date": str(msg["Date"] or ""),
        "message_id": str(msg["Message-ID"] or ""), "body": body.strip(), "attachments": atts,
    }
    typed, assoc = [], []
    if frm:
        f["from_name"], f["from_addr"] = frm[0]
        typed.append(("from_addr", "EMAIL"))
        if f["from_name"]:
            typed.append(("from_name", "PERSON"))
            assoc.append(("from_name", "ASSOCIATED_WITH", "from_addr"))
    if to:
        f["to_name"], f["to_addr"] = to[0]
        typed.append(("to_addr", "EMAIL"))
        if f["to_name"]:
            typed.append(("to_name", "PERSON"))
            assoc.append(("from_name", "ASSOCIATED_WITH", "to_addr"))
    if cc:
        f["cc_addr"] = cc[0][1]
        typed.append(("cc_addr", "EMAIL"))
    return ParsedRecord("MAIL", "EMAIL_MESSAGE", when, start, end, chunk, f,
                        f"{f.get('from_addr', '?')} → {f.get('to_addr', '?')}: {f['subject'][:80]}",
                        typed=typed, text_fields=["subject", "body"], assoc=assoc, time_precision=prec)
