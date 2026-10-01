"""PDF text extraction.

Uses pypdf when available. If it is not installed, or the PDF is scanned/image-only, the
file is recorded as metadata only and flagged so the evidence detail view can say that text
was not extracted (never fabricated). VIVAD never executes or renders attachments.
"""
from pathlib import Path

from .common import ParseError, ParsedRecord, ParseResult

MAX_PAGES = 200


def _extract(path: Path) -> tuple[list[str], int, str]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return [], 0, "PDF TEXT EXTRACTION UNAVAILABLE (pypdf not installed); metadata only"
    try:
        reader = PdfReader(str(path))
        pages = []
        for i, page in enumerate(reader.pages):
            if i >= MAX_PAGES:
                break
            try:
                pages.append(page.extract_text() or "")
            except Exception:  # noqa: BLE001
                pages.append("")
        return pages, len(reader.pages), ""
    except Exception as e:  # noqa: BLE001
        return [], 0, f"PDF COULD NOT BE READ: {type(e).__name__}"


def parse(path: Path, filename: str) -> ParseResult:
    pages, total_pages, warning = _extract(path)
    if not pages and warning:
        # Metadata-only record: filename and page count if known, so provenance still exists.
        rec = ParsedRecord("PDF", "PDF_DOCUMENT", None, 1, 1, f"[pdf] {filename}",
                           {"filename": filename, "pages": total_pages}, f"PDF {filename} ({total_pages or '?'} pages)",
                           text_fields=[])
        return ParseResult("DOCUMENT", [rec], 1, [warning], extracted_text=False)
    recs = []
    for pno, text in enumerate(pages, 1):
        for lno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            recs.append(ParsedRecord("PDF", "PDF_LINE", None, pno, pno, line.rstrip(),
                                     {"page": pno, "text": line.strip()}, line.strip()[:140],
                                     text_fields=["text"]))
    if not recs:
        rec = ParsedRecord("PDF", "PDF_DOCUMENT", None, 1, 1, f"[pdf] {filename}",
                           {"filename": filename, "pages": total_pages}, f"PDF {filename} — no extractable text",
                           text_fields=[])
        return ParseResult("DOCUMENT", [rec], 1, ["PDF contains no extractable text (possibly scanned)"], extracted_text=False)
    return ParseResult("DOCUMENT", recs, total_pages, [], extracted_text=True)
