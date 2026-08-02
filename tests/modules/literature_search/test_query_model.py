import json
from datetime import UTC, datetime

import pytest

from app.modules.literature_search.service import LiteratureSearchService


async def extractor(payload: dict[str, object]):
    async def run(_: str) -> str:
        return json.dumps(payload)

    return run


@pytest.mark.asyncio
async def test_complete_topic_returns_editable_model_candidate():
    service = LiteratureSearchService(
        None,  # type: ignore[arg-type]
        candidate_extractor=await extractor(
            {
                "topic": "近三年胃癌免疫治疗耐药机制",
                "disease": "胃癌",
                "intervention": "免疫治疗",
                "mechanism": "耐药机制",
                "date_range": {"start_year": 2020, "end_year": 2024},
                "study_types": ["机制研究"],
                "language": ["中文", "English"],
                "retmax": 80,
            }
        ),
    )

    result = await service.parse_query("近三年胃癌免疫治疗耐药机制")

    assert result.raw_topic == "近三年胃癌免疫治疗耐药机制"
    assert result.candidate.disease == "胃癌"
    assert result.candidate.date_range.start_year == datetime.now(UTC).year - 2
    assert result.candidate.date_range.end_year == datetime.now(UTC).year
    assert result.candidate.retmax == 80
    assert result.candidate_source == "model_candidate"


@pytest.mark.asyncio
async def test_disease_only_does_not_force_pico():
    service = LiteratureSearchService(
        None,  # type: ignore[arg-type]
        candidate_extractor=await extractor({"topic": "胃癌", "disease": "胃癌"}),
    )

    result = await service.parse_query("胃癌")

    assert result.candidate.disease == "胃癌"
    assert result.candidate.intervention is None
    assert any("研究类型" in question for question in result.clarification_questions)


@pytest.mark.asyncio
async def test_relative_date_expression_is_resolved_visibly():
    service = LiteratureSearchService(None, candidate_extractor=await extractor({"topic": "近三年肺癌"}))  # type: ignore[arg-type]

    result = await service.parse_query("近三年肺癌")

    assert result.candidate.date_range.original_expression == "近三年"
    assert result.candidate.date_range.end_year == datetime.now(UTC).year


@pytest.mark.asyncio
async def test_unknown_fields_are_ignored_and_user_edits_are_preserved():
    service = LiteratureSearchService(
        None,  # type: ignore[arg-type]
        candidate_extractor=await extractor({"topic": "胃癌", "disease": "胃癌", "hidden_query": "never use"}),
    )

    result = await service.parse_query("胃癌")
    edited = result.candidate.model_copy(update={"retmax": 100, "exclusions": ["动物"]})

    assert not hasattr(result.candidate, "hidden_query")
    assert edited.retmax == 100
    assert edited.exclusions == ["动物"]


@pytest.mark.asyncio
async def test_invalid_model_json_falls_back_without_inventing_entities():
    async def invalid(_: str) -> str:
        return "not-json"

    result = await LiteratureSearchService(None, candidate_extractor=invalid).parse_query("近三年胃癌")  # type: ignore[arg-type]

    assert result.candidate_source == "rule_fallback"
    assert result.candidate.topic == "近三年胃癌"
    assert result.candidate.disease is None
