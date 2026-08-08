import pytest

from app.integrations.llm.schemas import LLMResponse
from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.orchestrator import RecommendationService
from app.modules.recommendation.reason_fusion import RecommendationReasonService


class Executor:
    async def execute(self, query: str, *, retmax: int):
        return [
            CitationItem(
                pmid="12345678",
                title="Verified title",
                authors=["Smith J"],
                year=2024,
                abstract="The intervention improved the outcome.",
                has_abstract=True,
                verified=True,
            )
        ], 1


class LLM:
    async def chat(self, messages):
        return LLMResponse(
            text="PMID 12345678 的 Verified title 很重要。",
            provider="test",
            model="test",
            elapsed_seconds=0,
        )

    async def aclose(self) -> None:
        return None


@pytest.mark.asyncio
async def test_orchestrator_keeps_metadata_server_owned_when_llm_leaks() -> None:
    service = RecommendationService(
        executor=Executor(),
        reason_service=RecommendationReasonService(llm=LLM()),
    )

    response = await service.recommend("肺癌")

    assert response.items[0].citation.pmid == "12345678"
    assert "12345678" not in response.items[0].recommendation_reason
    assert response.status == "completed_with_warnings"


class EmptyExecutor:
    async def execute(self, query: str, *, retmax: int):
        return [], 0


@pytest.mark.asyncio
async def test_orchestrator_marks_empty_evidence_with_warning() -> None:
    response = await RecommendationService(executor=EmptyExecutor()).recommend("肺癌")

    assert response.items == []
    assert response.status == "completed_with_warnings"
    assert response.warnings == ["未找到可验证文献"]
