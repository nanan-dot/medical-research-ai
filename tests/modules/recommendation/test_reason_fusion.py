import pytest

from app.integrations.llm.schemas import LLMResponse
from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.reason_fusion import RecommendationReasonService


class FakeLLM:
    def __init__(self, text: str | None = None, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.messages: list[str] = []

    async def chat(self, messages):
        self.messages.append(messages[-1].content)
        if self.error:
            raise self.error
        return LLMResponse(text=self.text or "摘要支持该干预的研究价值。", provider="test", model="test", elapsed_seconds=0)


def _item(**overrides) -> CitationItem:
    values = {
        "pmid": "12345678",
        "doi": "10.1000/example",
        "title": "Real title",
        "authors": ["Smith J"],
        "year": 2024,
        "has_abstract": True,
        "abstract": "The abstract supports the intervention in the studied population.",
        "verified": True,
    }
    values.update(overrides)
    return CitationItem(**values)


@pytest.mark.asyncio
async def test_reason_uses_abstract_but_returns_server_metadata() -> None:
    llm = FakeLLM("摘要支持该干预的研究价值。")
    service = RecommendationReasonService(llm=llm)

    result = await service.fuse([_item()])

    assert result[0].citation.pmid == "12345678"
    assert result[0].recommendation_reason == "摘要支持该干预的研究价值。"
    assert "Real title" not in llm.messages[0]


@pytest.mark.asyncio
async def test_metadata_leak_is_replaced_with_safe_fallback() -> None:
    llm = FakeLLM("PMID 12345678 的 Real title 由 Smith J 在 2024 年发表。")

    result = await RecommendationReasonService(llm=llm).fuse([_item()])

    assert "12345678" not in result[0].recommendation_reason
    assert "未采用模型输出" in result[0].recommendation_reason


@pytest.mark.asyncio
async def test_empty_abstract_uses_deterministic_reason_without_llm() -> None:
    llm = FakeLLM()
    result = await RecommendationReasonService(llm=llm).fuse([_item(has_abstract=False)])

    assert "无摘要" in result[0].recommendation_reason
    assert llm.messages == []
