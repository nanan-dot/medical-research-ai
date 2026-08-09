"""推荐请求编排：真实检索结果装配与理由融合。"""

from __future__ import annotations

from app.modules.recommendation.reason_fusion import RecommendationReasonService
from app.modules.recommendation.schema import (
    RecommendationItem,
    RecommendationResponse,
    RecommendationStatus,
)
from app.modules.recommendation.service import (
    RecommendationEvidenceService,
    RecommendationExecutor,
)


class RecommendationService:
    def __init__(
        self,
        *,
        executor: RecommendationExecutor,
        reason_service: RecommendationReasonService | None = None,
    ) -> None:
        self._evidence = RecommendationEvidenceService(executor=executor)
        self._reason_service = reason_service

    async def recommend(
        self, query: str, *, candidate_count: int = 5
    ) -> RecommendationResponse:
        evidence = await self._evidence.search(query, candidate_count=candidate_count)
        warnings = list(evidence.warnings)
        if self._reason_service is None:
            reasons = [
                "已通过 PubMed 元数据验证；当前未生成摘要依据推荐理由。"
                for _ in evidence.items
            ]
        else:
            fused = await self._reason_service.fuse(evidence.items)
            reasons = [entry.recommendation_reason for entry in fused]
        items = [
            RecommendationItem(citation=item, recommendation_reason=reason)
            for item, reason in zip(evidence.items, reasons, strict=True)
        ]
        if any(
            "未采用模型输出" in reason or "LLM理由生成失败" in reason
            for reason in reasons
        ):
            warnings.append("部分推荐理由未采用模型输出")
        status: RecommendationStatus = (
            "completed" if not warnings else "completed_with_warnings"
        )
        return RecommendationResponse(
            query=query,
            status=status,
            items=items,
            warnings=list(dict.fromkeys(warnings)),
        )
