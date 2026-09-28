"""论文与期刊指标候选的确定性内存匹配。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from app.modules.literature_search.journal_metric_normalization import (
    normalize_journal_name,
)
from app.modules.literature_search.schema import CitationItem

MatchMethod = Literal[
    "issn_l_exact", "issn_exact", "eissn_exact", "normalized_title_exact"
]


class MetricCandidate(Protocol):
    journal_key: str
    issn_l: str | None
    issn: str | None
    eissn: str | None
    normalized_journal_name: str | None


@dataclass(frozen=True)
class JournalMetricMatch:
    status: Literal["matched", "not_found", "ambiguous"]
    method: MatchMethod | None = None
    journal_key: str | None = None


def match_journal_metric(
    item: CitationItem, candidates: Sequence[MetricCandidate]
) -> JournalMetricMatch:
    """按固定优先级匹配；同级多键时拒绝猜测。"""
    identity_values = {value for value in (item.issn_l, item.issn, item.eissn) if value}
    normalized_title = normalize_journal_name(item.journal)
    rules: list[tuple[MatchMethod, str | None]] = [
        ("issn_l_exact", item.issn_l),
        ("issn_exact", item.issn),
        ("eissn_exact", item.eissn),
    ]
    for method, paper_value in rules:
        if not paper_value:
            continue
        matched = [
            candidate
            for candidate in candidates
            if paper_value in {candidate.issn_l, candidate.issn, candidate.eissn}
        ]
        result = _resolve(method, matched)
        if result is not None:
            return result
    # 论文任一 ISSN 允许交叉命中，但方法仍反映论文侧最早可用字段。
    if identity_values:
        method = next(method for method, value in rules if value)
        matched = [
            candidate
            for candidate in candidates
            if identity_values.intersection(
                {candidate.issn_l, candidate.issn, candidate.eissn}
            )
        ]
        result = _resolve(method, matched)
        if result is not None:
            return result
    if normalized_title:
        result = _resolve(
            "normalized_title_exact",
            [
                candidate
                for candidate in candidates
                if candidate.normalized_journal_name == normalized_title
            ],
        )
        if result is not None:
            return result
    return JournalMetricMatch(status="not_found")


def _resolve(
    method: MatchMethod, candidates: Sequence[MetricCandidate]
) -> JournalMetricMatch | None:
    keys = {candidate.journal_key for candidate in candidates}
    if not keys:
        return None
    if len(keys) > 1:
        return JournalMetricMatch(status="ambiguous", method=method)
    return JournalMetricMatch(
        status="matched", method=method, journal_key=next(iter(keys))
    )
