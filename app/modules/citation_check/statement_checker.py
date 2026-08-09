"""陈述级引用覆盖与主题关键词核验。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class StatementCheckResult:
    status: str
    citation_ids: list[str]
    replacement_suggested: bool
    notes: list[str]


def check_statement(
    statement: str, citation_ids: list[str], *, topic: str = ""
) -> StatementCheckResult:
    if not citation_ids:
        return StatementCheckResult("no_citation", [], False, ["请人工补充或核验引用"])
    if topic and not _has_topic_overlap(statement, topic):
        return StatementCheckResult(
            "topic_mismatch", citation_ids, False, ["引用主题需人工核验"]
        )
    return StatementCheckResult("ok", citation_ids, False, [])


def _has_topic_overlap(statement: str, topic: str) -> bool:
    terms = {term.lower() for term in topic.split() if term}
    text = statement.lower()
    return bool(terms) and any(term in text for term in terms)
