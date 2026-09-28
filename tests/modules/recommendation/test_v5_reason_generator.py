"""Acceptance tests for evidence-constrained optional narration."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.integrations.llm.schemas import LLMResponse
from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.reason_generator import RecommendationNarrator


@pytest.mark.asyncio
async def test_llm_failure_retains_deterministic_reason() -> None:
    llm = SimpleNamespace(chat=AsyncMock(side_effect=RuntimeError("offline")))
    result = await RecommendationNarrator(llm).render(
        citation=CitationItem(
            pmid="1", title="Study", abstract="Evidence", has_abstract=True
        ),
        intent={"disease": ["cancer"]},
        evidence={"matches": []},
        fallback_headline="确定性标题",
        fallback_narrative="这是完全由结构化证据生成的确定性推荐理由。",
    )
    assert result.headline == "确定性标题"
    assert result.limitation == "llm_narration_unavailable"


@pytest.mark.asyncio
async def test_llm_cannot_inject_new_numeric_claim() -> None:
    llm = SimpleNamespace(
        chat=AsyncMock(
            return_value=SimpleNamespace(
                text='{"headline":"候选","narrative":"疗效提高99%，因此应当采用该治疗方案。"}'
            )
        )
    )
    result = await RecommendationNarrator(llm).render(
        citation=CitationItem(
            pmid="1", title="Study", abstract="Evidence", has_abstract=True
        ),
        intent={"disease": ["cancer"]},
        evidence={"matches": []},
        fallback_headline="回退",
        fallback_narrative="结构化证据不足，保留确定性理由。",
    )
    assert result.headline == "回退"
    assert result.limitation == "llm_narration_rejected"


@pytest.mark.asyncio
async def test_valid_llm_wording_can_only_replace_wording_fields() -> None:
    narrative = "该候选与已确认的疾病、人群和结局维度相符，研究设计也与问题类型匹配；其新增价值来自当前结果快照及阅读计划均未覆盖该记录，现有证据仅支持将其列为待核验候选，后续仍需阅读全文并评估方法学质量。"
    llm = SimpleNamespace(
        chat=AsyncMock(
            return_value=LLMResponse(
                text='{"headline":"结构化证据支持的新增候选","narrative":"'
                + narrative
                + '"}',
                provider="test",
                model="test",
                elapsed_seconds=0,
            )
        )
    )
    result = await RecommendationNarrator(llm).render(
        citation=CitationItem(
            pmid="1", title="Study", abstract="Evidence", has_abstract=True
        ),
        intent={"disease": ["cancer"]},
        evidence={"matches": []},
        fallback_headline="回退",
        fallback_narrative="结构化证据不足，保留确定性理由。",
    )
    assert result.headline == "结构化证据支持的新增候选"
    assert result.narrative == narrative
    assert result.limitation is None


@pytest.mark.asyncio
async def test_llm_retries_once_when_first_wording_repeats_article_identity() -> None:
    narrative = "该候选与已确认的疾病和干预措施维度相符，且未被当前结果快照覆盖；现有信息支持将其作为新增待核验候选，后续仍需结合全文与研究设计进一步判断其证据适配程度。"
    llm = SimpleNamespace(
        chat=AsyncMock(
            side_effect=[
                LLMResponse(
                    text='{"headline":"Study","narrative":"' + narrative + '"}',
                    provider="test", model="test", elapsed_seconds=0,
                ),
                LLMResponse(
                    text='```json\n{"headline":"结构化证据支持的新增候选","narrative":"' + narrative + '"}\n```',
                    provider="test", model="test", elapsed_seconds=0,
                ),
            ]
        )
    )
    result = await RecommendationNarrator(llm).render(
        citation=CitationItem(pmid="1", title="Study", abstract="Evidence", has_abstract=True),
        intent={"disease": ["cancer"]}, evidence={"matches": []},
        fallback_headline="回退", fallback_narrative="结构化证据不足，保留确定性理由。",
    )
    assert result.headline == "结构化证据支持的新增候选"
    assert result.limitation is None
    assert llm.chat.await_count == 2
