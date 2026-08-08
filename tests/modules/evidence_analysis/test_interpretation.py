"""Offline validation tests for model-produced evidence interpretations."""

import json

import pytest

from app.modules.comparison.shared import SourceRef
from app.modules.evidence_analysis.interpretation import parse_grounded_interpretation
from app.modules.evidence_analysis.schema import (
    ResearchTypeStatisticRead,
    StatisticsLayerRead,
    TopicStatisticRead,
)


def _statistics() -> StatisticsLayerRead:
    return StatisticsLayerRead(
        high_frequency_topics=[
            TopicStatisticRead(
                topic="EGFR", count=3, year_range="2021-2023", trend="insufficient",
                basis="统计自 3 篇文献的主题字段", research_types={"RCT": 2, "队列": 1}
            )
        ],
        recent_growth_topics=[],
        research_type_distribution=[ResearchTypeStatisticRead(research_type="RCT", count=2, basis="统计自 3 篇文献的研究类型字段")],
    )


def _valid_item() -> dict[str, object]:
    return {
        "statement": "在当前检索结果中，EGFR 相关研究的结论需按 RCT 与队列研究分别解读。",
        "confidence": "medium",
        "evidence": [{"pmid": "12345", "locator": "matrix_cell"}],
        "statistics_basis": ["主题 EGFR: 3 篇, 趋势 insufficient"],
        "research_types": ["RCT", "队列"],
    }


def test_interpretation_requires_parseable_bound_evidence_and_statistics() -> None:
    raw = json.dumps({"consistencies": [_valid_item()], "conflicts": [], "limitations": [], "gaps": [], "search_questions": []})

    parsed = parse_grounded_interpretation(raw, _statistics(), [SourceRef(pmid="12345", locator="matrix_cell")])

    assert parsed.consistencies[0].evidence[0].pmid == "12345"


def test_interpretation_rejects_prohibited_overclaiming_words() -> None:
    item = _valid_item()
    item["statement"] = "这是空白领域。"
    raw = json.dumps({"consistencies": [], "conflicts": [], "limitations": [], "gaps": [item], "search_questions": []})

    with pytest.raises(ValueError, match="prohibited"):
        parse_grounded_interpretation(raw, _statistics(), [SourceRef(pmid="12345", locator="matrix_cell")])


def test_interpretation_rejects_evidence_outside_selected_matrix() -> None:
    item = _valid_item()
    item["evidence"] = [{"pmid": "67890", "locator": "matrix_cell"}]
    raw = json.dumps({"consistencies": [item], "conflicts": [], "limitations": [], "gaps": [], "search_questions": []})

    with pytest.raises(ValueError, match="not present"):
        parse_grounded_interpretation(raw, _statistics(), [SourceRef(pmid="12345", locator="matrix_cell")])
