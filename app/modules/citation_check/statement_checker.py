"""陈述级引用覆盖与主题关键词核验。"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StatementCheckResult:
    status: str
    citation_ids: list[str]
    replacement_suggested: bool
    notes: list[str]

    evidence_spans: list[str] | None = None


def check_statement(
    statement: str, citation_ids: list[str], *, topic: str = ""
) -> StatementCheckResult:
    if not citation_ids:
        return StatementCheckResult("no_citation", [], False, ["请人工补充或核验引用"])
    if topic and not _has_topic_overlap(statement, topic):
        return StatementCheckResult(
            "topic_mismatch", citation_ids, False, ["引用主题需人工核验"]
        )
    return StatementCheckResult("partially_supported", citation_ids, False, ["未提供可核验的证据片段"], [])

def assess_support(statement: str, citation_ids: list[str], evidence_spans: list[str], *, topic: str = "") -> StatementCheckResult:
    """Return conservative support labels without inferring unstated medical facts."""
    base = check_statement(statement, citation_ids, topic=topic)
    if base.status in {"no_citation", "topic_mismatch"}: return StatementCheckResult("unverifiable", citation_ids, base.replacement_suggested, base.notes, evidence_spans)
    if not evidence_spans: return base
    normalized = " ".join(evidence_spans).lower()
    numbers = re.findall(r"\b\d+(?:\.\d+)?\b", statement)
    if numbers and any(number not in normalized for number in numbers): return StatementCheckResult("unsupported", citation_ids, True, ["陈述数值未见于提供的证据片段"], evidence_spans)
    if statement.lower() in normalized: return StatementCheckResult("supported", citation_ids, False, [], evidence_spans)
    return StatementCheckResult("partially_supported", citation_ids, False, ["证据片段与陈述仅部分重叠，需人工复核"], evidence_spans)


def _has_topic_overlap(statement: str, topic: str) -> bool:
    terms = {term.lower() for term in topic.split() if term}
    text = statement.lower()
    return bool(terms) and any(term in text for term in terms)
