"""Generic JSON parsing: a document, list or nested structure becomes one record per leaf item."""
import json
from pathlib import Path

from .common import ParseError, ParsedRecord, ParseResult, parse_time, read_text

TIME_KEYS = ("timestamp", "time", "date", "datetime", "created_at", "paid_at", "issued_at")


def _line_index(text: str) -> dict:
    idx = {}
    for i, ln in enumerate(text.splitlines(), 1):
        s = ln.strip().rstrip(",")
        if s and s not in idx:
            idx[s] = i
    return idx


def parse(path: Path, filename: str) -> ParseResult:
    text = read_text(path)
    if not text.strip():
        raise ParseError("EMPTY FILE")
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as e:
        raise ParseError(f"MALFORMED JSON: {e.msg} at line {e.lineno} col {e.colno}")
    idx = _line_index(text)
    total = len(text.splitlines())
    items = doc if isinstance(doc, list) else ([doc] if not isinstance(doc, dict) else _flatten(doc))
    recs = []
    for it in items:
        ln = idx.get(json.dumps(it))
        f = it if isinstance(it, dict) else {"value": it}
        when, prec = _time_of(f)
        recs.append(ParsedRecord("JSON", "JSON_ITEM", when, ln, ln, json.dumps(it), f,
                                 _summary(f) or json.dumps(it)[:140], text_fields=list(f.keys()), time_precision=prec))
    if not recs:
        raise ParseError("NO ITEMS IN JSON DOCUMENT")
    return ParseResult("STRUCTURED", recs, total, [])


def _flatten(doc: dict):
    items = []
    for k, v in doc.items():
        if isinstance(v, list) and v and all(isinstance(x, dict) for x in v):
            items.extend(v)
        else:
            items.append({k: v})
    return items


def _time_of(f: dict):
    for k in TIME_KEYS:
        if k in f:
            t, p = parse_time(f[k])
            if t:
                return t, p
    return None, "second"


def _summary(f: dict) -> str:
    return " · ".join(f"{k}={v}" for k, v in list(f.items())[:5] if not isinstance(v, (dict, list)))[:140]
