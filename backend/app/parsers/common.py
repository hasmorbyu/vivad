"""Shared parser types and helpers. Parsers never invent values: unparseable times become None."""
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))


class ParseError(Exception):
    pass


@dataclass
class ParsedRecord:
    prefix: str
    record_type: str
    event_time: str | None
    line_no: int | None
    line_end: int | None
    raw_text: str
    fields: dict
    summary: str
    typed: list = field(default_factory=list)       # (field, entity_type)
    text_fields: list = field(default_factory=list)  # free-text fields to scan
    assoc: list = field(default_factory=list)        # (src_field, label, dst_field)
    time_precision: str = "second"


@dataclass
class ParseResult:
    source_type: str
    records: list
    line_count: int
    warnings: list = field(default_factory=list)
    extracted_text: bool = True


def read_text(path: Path) -> str:
    data = Path(path).read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("latin-1")


_FORMATS = [
    "%d/%m/%Y, %H:%M:%S", "%d/%m/%Y, %H:%M", "%d/%m/%y, %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d %b %Y %H:%M",
    "%d %b %Y %H:%M:%S", "%d/%m/%Y, %I:%M %p", "%d/%m/%y, %I:%M %p", "%d %B %Y %H:%M",
]
_DATE_ONLY = ["%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%b-%Y", "%d %b %Y", "%d %B %Y"]


def parse_time(v) -> tuple[str | None, str]:
    """Return (ISO string with +05:30, precision). Naive times are assumed IST."""
    if v is None:
        return None, "second"
    s = str(v).strip()
    if not s:
        return None, "second"
    dt = None
    if re.fullmatch(r"\d{10,13}", s):
        n = int(s)
        dt = datetime.fromtimestamp(n / 1000 if n > 1e11 else n, tz=timezone.utc)
    if dt is None:
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
                return s, "date"
        except ValueError:
            pass
    if dt is None:
        for f in _FORMATS:
            try:
                dt = datetime.strptime(s, f)
                break
            except ValueError:
                continue
    if dt is None:
        for f in _DATE_ONLY:
            try:
                return datetime.strptime(s, f).strftime("%Y-%m-%d"), "date"
            except ValueError:
                continue
    if dt is None:
        try:
            dt = parsedate_to_datetime(s)
        except (TypeError, ValueError):
            return None, "second"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=IST)
    return dt.astimezone(IST).isoformat(timespec="seconds"), "second"


def to_amount(v) -> float | None:
    try:
        return float(str(v).replace(",", "").replace("₹", "").replace("INR", "").replace("Rs", "").replace("Rs.", "").strip())
    except (ValueError, AttributeError):
        return None


def rupees(v) -> str:
    a = to_amount(v)
    return f"₹{a:,.2f}" if a is not None else str(v)
