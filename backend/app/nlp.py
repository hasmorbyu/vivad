"""Deterministic entity and fact extraction for VIVAD.

This is the counterpart of AMADEUS's extraction layer: pure regex/rule based, no AI. It
pulls amounts, dates, organisations, locations, people and identifiers out of evidence text
so claims can be linked to documentary support deterministically. The original value is
always preserved alongside its canonical form.
"""
import re

from .parsers.common import parse_time, to_amount

_AMOUNT = re.compile(r"(?:₹|INR|Rs\.?)\s?([\d][\d,]*(?:\.\d{1,2})?)", re.I)
_AMOUNT_K = re.compile(r"\b(\d+(?:\.\d+)?)\s?k\b", re.I)
_DATE = re.compile(r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b", re.I)
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
_UPI = re.compile(r"(?<![\w.@-])([A-Za-z0-9._-]{2,40}@[A-Za-z][A-Za-z0-9]{1,20})\b(?!\.[A-Za-z])")
_PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
_ACCT = re.compile(r"\b(?:A/C|ACCT|ACCOUNT)[\s:#-]*([A-Z0-9][A-Z0-9-]{4,20})\b", re.I)
_TXN = re.compile(r"\b(?:UPI|Ref(?:erence)?(?:\s+No\.?)?|txn(?:\s*id)?|UTR)[:#\s/]+([A-Z0-9]{8,24})\b", re.I)
_DOCID = re.compile(r"\b(?:Agreement|Invoice|Receipt|Policy|Order|Bill)\s*(?:No\.?|#|ID)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9/-]{3,20})\b", re.I)
_ORG = re.compile(r"\b((?:[A-Z][A-Za-z&.]+(?:\s+|$)){1,5}(?:Ltd|Limited|LLP|Pvt|Private|Bank|Associates|Enterprises|Properties|Realty|Company|Services|Co\.|Corporation|Trust|Society)\.?)\b")
_LOCATION = re.compile(r"\b([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+){0,3}\s+(?:Nagar|Road|Street|Layout|Colony|Apartments|Complex|District|City|Society|Lane|Cross|Park|Estate|Block))\b")

TYPES = ("AMOUNT", "DATE", "EMAIL", "UPI", "PHONE", "ACCOUNT", "TRANSACTION_ID", "DOCUMENT_ID", "PERSON", "ORGANIZATION", "LOCATION")


def norm_phone(v: str) -> str | None:
    d = re.sub(r"\D", "", str(v))
    if not d:
        return None
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if len(d) == 10 and d[0] in "6789":
        return "+91" + d
    if 3 <= len(d) <= 6:
        return d
    if str(v).strip().startswith("+") and 7 <= len(d) <= 15:
        return "+" + d
    return None


def canonical(etype: str, value) -> str | None:
    v = str(value).strip() if value is not None else ""
    if not v:
        return None
    if etype == "PHONE":
        p = norm_phone(v)
        return f"phone:{p}" if p else None
    if etype == "UPI":
        u = v.lower()
        return f"upi:{u}" if re.match(r"^[a-z0-9][a-z0-9._-]{1,40}@[a-z][a-z0-9]{1,20}$", u) else None
    if etype in ("ACCOUNT", "TRANSACTION_ID", "DOCUMENT_ID"):
        return f"{etype.lower()}:{re.sub(r'[^A-Za-z0-9/-]', '', v).upper()}"
    if etype == "EMAIL":
        e = v.lower()
        return f"email:{e}" if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", e) else None
    if etype == "AMOUNT":
        a = to_amount(v)
        return f"amount:{a:.2f}" if a is not None else None
    if etype == "DATE":
        iso, _ = parse_time(v)
        return f"date:{iso}" if iso else None
    if etype == "PERSON":
        name = " ".join(v.lower().split())
        return f"person:{name}" if name else None
    if etype == "ORGANIZATION":
        return f"org:{' '.join(v.lower().split()).rstrip('.')}"
    if etype == "LOCATION":
        return f"location:{' '.join(v.lower().split())}"
    return None


def scan_text(text: str) -> list[tuple[str, str]]:
    """Return (type, original) pairs. Consumed spans are masked to avoid double matches."""
    out: list[tuple[str, str]] = []
    work = text or ""

    def take(rx, etype, grp=1, transform=None):
        nonlocal work
        for m in list(rx.finditer(work)):
            val = m.group(grp)
            if val:
                out.append((etype, transform(val) if transform else val.strip()))
        work = rx.sub(lambda m: " " * len(m.group(0)), work)

    take(_EMAIL, "EMAIL", 0)
    take(_UPI, "UPI")
    take(_TXN, "TRANSACTION_ID")
    take(_DOCID, "DOCUMENT_ID")
    take(_ACCT, "ACCOUNT")
    take(_AMOUNT_K, "AMOUNT", transform=lambda v: str(float(v) * 1000))
    take(_AMOUNT, "AMOUNT")
    take(_DATE, "DATE")
    take(_PHONE, "PHONE")
    take(_LOCATION, "LOCATION")
    take(_ORG, "ORGANIZATION")
    return out


def extract_facts(text: str) -> dict:
    """Structured view used by the evidence detail and claim extraction."""
    ents = scan_text(text)
    amounts, dates, people, orgs, locations = [], [], [], [], []
    for etype, value in ents:
        if etype == "AMOUNT":
            a = to_amount(value)
            if a is not None:
                amounts.append(a)
        elif etype == "DATE":
            iso, prec = parse_time(value)
            if iso:
                dates.append({"value": value, "iso": iso, "precision": prec})
        elif etype == "PERSON":
            people.append(value)
        elif etype == "ORGANIZATION":
            orgs.append(value)
        elif etype == "LOCATION":
            locations.append(value)
    return {"entities": [{"type": t, "value": v, "canonical": canonical(t, v)} for t, v in ents],
            "amounts": amounts, "dates": dates, "people": people, "organizations": orgs, "locations": locations}
