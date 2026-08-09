"""Evidence-analysis deterministic statistics.

This module deliberately contains no database or model calls so statistical clues remain
repeatable and independently testable.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Literal

Trend = Literal["up", "flat", "down", "insufficient"]
MIN_TREND_DOCUMENTS = 5


@dataclass(frozen=True)
class StatisticalDocument:
    """Minimal normalized document data used by pure statistic functions."""

    document_id: int
    year: int | None
    research_type: str | None
    topics: tuple[str, ...]


@dataclass(frozen=True)
class TopicStatistic:
    """A topic-frequency observation, not a medical conclusion."""

    topic: str
    count: int
    year_range: str | None
    trend: Trend
    basis: str
    research_types: dict[str, int]


@dataclass(frozen=True)
class ResearchTypeStatistic:
    """Distribution of declared research types in the selected documents."""

    research_type: str
    count: int
    basis: str


def calculate_topic_statistics(
    documents: list[StatisticalDocument],
) -> list[TopicStatistic]:
    """Calculate per-topic frequency and conservative temporal direction."""
    topic_documents: dict[str, list[StatisticalDocument]] = defaultdict(list)
    for document in documents:
        for topic in set(_normalize_topics(document.topics)):
            topic_documents[topic].append(document)
    return [
        _build_topic_statistic(topic, matching_documents, len(documents))
        for topic, matching_documents in sorted(
            topic_documents.items(), key=lambda item: (-len(item[1]), item[0])
        )
    ]


def calculate_research_type_distribution(
    documents: list[StatisticalDocument],
) -> list[ResearchTypeStatistic]:
    """Count declared research types without treating unlike designs as equivalent."""
    counts = Counter(document.research_type or "未标注" for document in documents)
    total = len(documents)
    return [
        ResearchTypeStatistic(
            research_type=research_type,
            count=count,
            basis=f"统计自 {total} 篇文献的研究类型字段",
        )
        for research_type, count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]


def _build_topic_statistic(
    topic: str, documents: list[StatisticalDocument], total_documents: int
) -> TopicStatistic:
    years = [document.year for document in documents if document.year is not None]
    research_types = Counter(
        document.research_type or "未标注" for document in documents
    )
    return TopicStatistic(
        topic=topic,
        count=len(documents),
        year_range=_year_range(years),
        trend=_calculate_trend(years, len(documents)),
        basis=f"统计自 {total_documents} 篇文献的主题字段",
        research_types=dict(sorted(research_types.items())),
    )


def _normalize_topics(topics: tuple[str, ...]) -> list[str]:
    return [
        " ".join(topic.split())
        for topic in topics
        if topic.strip() and topic.strip() != "缺失"
    ]


def _year_range(years: list[int]) -> str | None:
    if not years:
        return None
    return f"{min(years)}-{max(years)}"


def _calculate_trend(years: list[int], document_count: int) -> Trend:
    if document_count < MIN_TREND_DOCUMENTS or len(years) < MIN_TREND_DOCUMENTS:
        return "insufficient"
    ordered_years = sorted(years)
    midpoint = (ordered_years[0] + ordered_years[-1]) / 2
    earlier_count = sum(year <= midpoint for year in ordered_years)
    later_count = len(ordered_years) - earlier_count
    if later_count > earlier_count:
        return "up"
    if later_count < earlier_count:
        return "down"
    return "flat"
