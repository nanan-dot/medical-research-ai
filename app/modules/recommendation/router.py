"""推荐 API 路由和请求级依赖边界。"""

from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import LLMClientError
from app.integrations.ollama.client import OllamaClient
from app.integrations.ollama.exceptions import OllamaError
from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.literature_search.pubmed_executor import PubMedExecutor
from app.modules.recommendation.orchestrator import RecommendationService
from app.modules.recommendation.reason_fusion import (
    ReasonLLM,
    RecommendationReasonService,
)
from app.modules.recommendation.schema import (
    RecommendationRequest,
    RecommendationResponse,
)
from app.modules.recommendation.service import RecommendationExecutor

router = APIRouter(prefix="/recommendations", tags=["recommendation"])


async def get_recommendation_service() -> AsyncIterator[RecommendationService]:
    pubmed = PubMedClient.from_settings()
    executor: RecommendationExecutor = PubMedExecutor(pubmed)
    llm: ReasonLLM | None = None
    try:
        if settings.DEFAULT_MODEL_PROVIDER == "ollama":
            llm = OllamaClient.from_settings()
        else:
            llm = LLMClient.from_settings()
        yield RecommendationService(
            executor=executor,
            reason_service=RecommendationReasonService(llm=llm),
        )
    except (LLMClientError, OllamaError):
        # 配置/本地模型不可用时保留真实检索路径，不隐式切换云端。
        yield RecommendationService(executor=executor)
    finally:
        await pubmed.aclose()
        if llm is not None:
            await llm.aclose()


@router.post("", response_model=RecommendationResponse)
async def create_recommendation(
    request: RecommendationRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationResponse:
    try:
        return await service.recommend(
            request.query, candidate_count=request.candidate_count
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except PubMedError as error:
        raise HTTPException(
            status_code=503, detail="PubMed service unavailable"
        ) from error
