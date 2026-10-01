"""Schema validation for AI output. Raw model output is never trusted or stored unvalidated."""
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class _Base(BaseModel):
    model_config = ConfigDict(extra="ignore")


class CitedText(_Base):
    text: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    basis: str = ""


class TextReason(_Base):
    text: str = ""
    reason: str = ""


class ContradictionOut(_Base):
    kind: str = "OTHER"
    title: str = ""
    evidence_ids: list[str] = Field(default_factory=list)
    explanation: str = ""
    basis: str = ""


class AnalysisOut(_Base):
    summary: str = ""
    facts_supported: list[CitedText] = Field(default_factory=list)
    claims_requiring_verification: list[TextReason] = Field(default_factory=list)
    potential_contradictions: list[ContradictionOut] = Field(default_factory=list)
    missing_information: list[TextReason] = Field(default_factory=list)
    possible_resolution_paths: list[CitedText] = Field(default_factory=list)
    hearing_questions: list[str] = Field(default_factory=list)


class SchemaResult(_Base):
    ok: bool
    data: AnalysisOut | None = None
    errors: list[str] = Field(default_factory=list)
    dropped_evidence_ids: list[str] = Field(default_factory=list)
    items_dropped: int = 0


def _clean_ids(ids, valid: set[str], dropped: list[str]) -> list[str]:
    out = []
    for i in ids or []:
        i = str(i).strip()
        if i in valid:
            out.append(i)
        elif i:
            dropped.append(i)
    return list(dict.fromkeys(out))


def validate_analysis(raw: dict, valid_evidence_ids: set[str]) -> SchemaResult:
    errors: list[str] = []
    try:
        out = AnalysisOut.model_validate(raw)
    except ValidationError as e:
        return SchemaResult(ok=False, errors=[f"{err['loc']}: {err['msg']}" for err in e.errors()[:10]])
    dropped: list[str] = []
    item_drops = 0
    kept = AnalysisOut(summary=str(out.summary or "")[:4000])
    for f in out.facts_supported:
        if not f.text.strip():
            item_drops += 1
            continue
        f.evidence_ids = _clean_ids(f.evidence_ids, valid_evidence_ids, dropped)
        kept.facts_supported.append(f)
    for c in out.claims_requiring_verification:
        if not c.text.strip():
            item_drops += 1
            continue
        kept.claims_requiring_verification.append(c)
    for c in out.potential_contradictions:
        if not (c.title.strip() or c.explanation.strip()):
            item_drops += 1
            continue
        c.evidence_ids = _clean_ids(c.evidence_ids, valid_evidence_ids, dropped)
        kept.potential_contradictions.append(c)
    kept.missing_information = [m for m in out.missing_information if m.text.strip()]
    for p in out.possible_resolution_paths:
        if not p.text.strip():
            item_drops += 1
            continue
        p.evidence_ids = _clean_ids(p.evidence_ids, valid_evidence_ids, dropped)
        kept.possible_resolution_paths.append(p)
    kept.hearing_questions = [q for q in out.hearing_questions if q.strip()][:20]
    if dropped:
        errors.append(f"dropped {len(dropped)} evidence id(s) not present in the case")
    return SchemaResult(ok=True, data=kept, errors=errors, dropped_evidence_ids=dropped, items_dropped=item_drops)
