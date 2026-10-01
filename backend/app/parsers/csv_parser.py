"""Generic CSV parsing. Every row becomes a record; a timestamp-like column, if present, is used.

VIVAD deals with payment records, invoices, statements and schedules, so the parser is
schema-agnostic: all columns are scanned as free text and any parseable time column is
promoted to the record's event time (date-only values stay date-only).
"""
import csv
import io
from pathlib import Path

from .common import ParseError, ParsedRecord, ParseResult, parse_time, read_text

TIME_KEYS = ("timestamp", "time", "date", "datetime", "payment_date", "due_date", "issued", "created")


def parse(path: Path, filename: str) -> ParseResult:
    text = read_text(path)
    if not text.strip():
        raise ParseError("EMPTY FILE")
    rd = csv.reader(io.StringIO(text))
    try:
        header = [h.strip().lower().replace(" ", "_") for h in next(rd)]
    except StopIteration:
        raise ParseError("EMPTY FILE")
    if not header:
        raise ParseError("MISSING HEADER ROW")
    time_col = next((h for h in header if h in TIME_KEYS), None)
    recs, warnings = [], []
    bad_time = bad_row = 0
    prev = rd.line_num
    for row in rd:
        start, end = prev + 1, rd.line_num
        prev = rd.line_num
        if not any(c.strip() for c in row):
            continue
        if len(row) != len(header):
            bad_row += 1
            row = (row + [""] * len(header))[: len(header)]
        f = {h: row[i].strip() for i, h in enumerate(header)}
        when, prec = parse_time(f[time_col]) if time_col else (None, "second")
        if time_col and when is None:
            bad_time += 1
        summary = " · ".join(f"{k}={v}" for k, v in list(f.items())[:4] if v)[:140]
        recs.append(ParsedRecord("ROW", "CSV_ROW", when, start, end, ",".join(row), f, summary or ",".join(row)[:140],
                                 text_fields=list(header), time_precision=prec))
    if bad_row:
        warnings.append(f"{bad_row} malformed rows padded/truncated")
    if bad_time:
        warnings.append(f"{bad_time} rows with unparseable time (left empty)")
    return ParseResult("SPREADSHEET", recs, len(text.splitlines()), warnings)
