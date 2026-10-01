"""Plain-text, chat-export and document parsing. Each line becomes a stable record."""
import re
from pathlib import Path

from .common import ParseError, ParsedRecord, ParseResult, parse_time, read_text

CHAT_RE = re.compile(r"^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?) - (.*)$")
BRACKET_TS = re.compile(r"^\[(\d{4}-\d{2}-\d{2}[ T]\d{1,2}:\d{2}(?::\d{2})?)\]\s*(?:-|:)?\s*(.*)$")
NOTE_TS = re.compile(r"^\[?(\d{1,2} [A-Z][a-z]{2} \d{4}[ ,]+\d{1,2}:\d{2})\]?\s*[-:]?\s*(.*)$")


def parse(path: Path, filename: str) -> ParseResult:
    text = read_text(path)
    if not text.strip():
        raise ParseError("EMPTY FILE")
    lines = text.splitlines()
    head = [l for l in lines[:80] if l.strip()]
    if head and sum(1 for l in head if CHAT_RE.match(l)) / len(head) > 0.4:
        return _chat(lines)
    return _document(lines)


def _chat(lines) -> ParseResult:
    recs, cur, bad = [], None, 0

    def flush():
        if cur:
            recs.append(_chat_record(cur))

    for i, line in enumerate(lines, 1):
        m = CHAT_RE.match(line)
        if m:
            flush()
            cur = {"date": m.group(1), "time": m.group(2), "rest": m.group(3), "start": i, "end": i, "extra": []}
        elif cur is not None:
            cur["extra"].append(line)
            cur["end"] = i
        elif line.strip():
            bad += 1
    flush()
    return ParseResult("CHAT", recs, len(lines), [f"{bad} lines before first message ignored"] if bad else [])


def _chat_record(c) -> ParsedRecord:
    when, prec = parse_time(f"{c['date']}, {c['time']}")
    rest = c["rest"]
    sm = re.match(r"^([^:]{1,40}?): (.*)$", rest)
    body = "\n".join([sm.group(2) if sm else rest] + c["extra"]).rstrip()
    raw = "\n".join([f"{c['date']}, {c['time']} - {rest}"] + c["extra"]).rstrip()
    if sm:
        sender = sm.group(1)
        f = {"sender": sender, "text": body}
        return ParsedRecord("MSG", "MESSAGE", when, c["start"], c["end"], raw, f, f"{sender}: {body[:120]}",
                            typed=[("sender", "PERSON")], text_fields=["text"], time_precision=prec)
    f = {"sender": "", "text": body}
    return ParsedRecord("MSG", "MESSAGE_SYSTEM", when, c["start"], c["end"], raw, f, f"[system] {body[:120]}",
                        text_fields=["text"], time_precision=prec)


def _document(lines) -> ParseResult:
    recs = []
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        body, when, prec = line.strip(), None, "second"
        m = BRACKET_TS.match(body) or NOTE_TS.match(body)
        if m:
            when, prec = parse_time(m.group(1).replace(",", ""))
            body = m.group(2) or body
        f = {"text": body}
        recs.append(ParsedRecord("DOC", "DOCUMENT_LINE", when, i, i, line.rstrip(), f, body[:140],
                                 text_fields=["text"], time_precision=prec))
    if not recs:
        raise ParseError("EMPTY FILE")
    return ParseResult("DOCUMENT", recs, len(lines), [])
