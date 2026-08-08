"""Offline unit tests for deterministic evidence-analysis statistics."""

from app.modules.evidence_analysis.statistics import (
    StatisticalDocument,
    calculate_research_type_distribution,
    calculate_topic_statistics,
)


def test_topic_frequency_and_research_type_distribution_are_calculated() -> None:
    documents = [
        StatisticalDocument(1, 2021, "RCT", ("EGFR", "生存")),
        StatisticalDocument(2, 2022, "队列", ("EGFR",)),
        StatisticalDocument(3, 2023, "RCT", ("EGFR", "生存")),
    ]

    topics = calculate_topic_statistics(documents)
    research_types = calculate_research_type_distribution(documents)

    assert topics[0].topic == "EGFR"
    assert topics[0].count == 3
    assert topics[0].year_range == "2021-2023"
    assert topics[0].research_types == {"RCT": 2, "队列": 1}
    assert [(item.research_type, item.count) for item in research_types] == [("RCT", 2), ("队列", 1)]


def test_trend_is_up_when_later_half_has_more_documents() -> None:
    documents = [
        StatisticalDocument(1, 2020, "队列", ("主题A",)),
        StatisticalDocument(2, 2021, "队列", ("主题A",)),
        StatisticalDocument(3, 2022, "队列", ("主题A",)),
        StatisticalDocument(4, 2022, "队列", ("主题A",)),
        StatisticalDocument(5, 2023, "队列", ("主题A",)),
    ]

    topic = calculate_topic_statistics(documents)[0]

    assert topic.trend == "up"


def test_trend_is_insufficient_below_minimum_document_count() -> None:
    documents = [
        StatisticalDocument(1, 2021, "队列", ("主题A",)),
        StatisticalDocument(2, 2022, "队列", ("主题A",)),
        StatisticalDocument(3, 2023, "队列", ("主题A",)),
        StatisticalDocument(4, 2024, "队列", ("主题A",)),
    ]

    topic = calculate_topic_statistics(documents)[0]

    assert topic.trend == "insufficient"
