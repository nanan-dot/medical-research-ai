"""Model-output validation for grounded evidence interpretations."""

from app.modules.comparison.shared import SourceRef
from app.modules.evidence_analysis.schema import InterpretationLayerRead, StatisticsLayerRead


def parse_grounded_interpretation(
    raw_json: str, statistics: StatisticsLayerRead, allowed_sources: list[SourceRef]
) -> InterpretationLayerRead:
    """Parse model JSON and reject unsupported sources or detached statistical claims."""
    interpretation = InterpretationLayerRead.model_validate_json(raw_json)
    allowed_source_keys = {_source_key(source) for source in allowed_sources}
    statistic_bases = _statistic_bases(statistics)
    for item in _all_items(interpretation):
        if not set(item.statistics_basis).issubset(statistic_bases):
            raise ValueError("Interpretation must cite an exact statistic from the statistics layer")
        for evidence in item.evidence:
            if _source_key(evidence) not in allowed_source_keys:
                raise ValueError("Interpretation evidence is not present in the selected matrix")
    for conflict in interpretation.conflicts:
        for evidence in [*conflict.supporting_evidence, *conflict.opposing_evidence]:
            if _source_key(evidence) not in allowed_source_keys:
                raise ValueError("Conflict evidence is not present in the selected matrix")
    return interpretation


def _statistic_bases(statistics: StatisticsLayerRead) -> set[str]:
    return {
        *[f"主题 {item.topic}: {item.count} 篇, 趋势 {item.trend}" for item in statistics.high_frequency_topics],
        *[f"研究类型 {item.research_type}: {item.count} 篇" for item in statistics.research_type_distribution],
    }


def _all_items(interpretation: InterpretationLayerRead) -> list:
    return [
        *interpretation.consistencies,
        *interpretation.conflicts,
        *interpretation.limitations,
        *interpretation.gaps,
        *interpretation.search_questions,
    ]


def _source_key(source: SourceRef) -> tuple[str | None, str | None, str]:
    return (source.pmid, source.doi, source.locator)
