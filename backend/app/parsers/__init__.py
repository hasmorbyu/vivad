"""Format dispatch for evidence parsing.

Text, CSV, JSON, email and PDF are parsed into records with provenance. Images, audio and
video are recorded as metadata only (VIVAD does not OCR or transcribe automatically); a
transcript or description can be supplied as a separate text document.
"""
from pathlib import Path

from . import csv_parser, email_parser, json_parser, pdf_parser, text_parser
from .common import ParseError, ParsedRecord, ParseResult  # noqa: F401

TEXT_EXT = {".txt", ".log", ".md", ".text"}
SHEET_EXT = {".csv", ".tsv"}
DATA_EXT = {".json"}
MAIL_EXT = {".eml", ".mbox"}
PDF_EXT = {".pdf"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}
VIDEO_EXT = {".mp4", ".mov", ".webm", ".avi", ".mkv"}

SUPPORTED = TEXT_EXT | SHEET_EXT | DATA_EXT | MAIL_EXT | PDF_EXT | IMAGE_EXT | AUDIO_EXT | VIDEO_EXT

MEDIA_SOURCE = {**{e: "IMAGE" for e in IMAGE_EXT}, **{e: "AUDIO" for e in AUDIO_EXT}, **{e: "VIDEO" for e in VIDEO_EXT}}


def _media(path: Path, filename: str, kind: str) -> ParseResult:
    size = path.stat().st_size
    rec = ParsedRecord("MEDIA", f"{kind}_FILE", None, 1, 1, f"[{kind.lower()}] {filename}",
                       {"filename": filename, "size": size}, f"{kind} {filename} ({size} bytes)",
                       text_fields=[])
    # The evidence detail view shows a preview from the original file; no text is inferred.
    return ParseResult(kind, [rec], 1, [f"{kind} recorded as metadata only; no automatic text extraction"], extracted_text=False)


def parse_file(path: Path, filename: str) -> ParseResult:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED:
        raise ParseError(f"UNSUPPORTED FILE TYPE '{ext or '(none)'}'")
    if ext in TEXT_EXT:
        return text_parser.parse(path, filename)
    if ext in SHEET_EXT:
        return csv_parser.parse(path, filename)
    if ext in DATA_EXT:
        return json_parser.parse(path, filename)
    if ext in MAIL_EXT:
        return email_parser.parse(path, filename)
    if ext in PDF_EXT:
        return pdf_parser.parse(path, filename)
    return _media(path, filename, MEDIA_SOURCE[ext])
