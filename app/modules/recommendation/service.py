"""推荐检索的真实 PubMed 证据装配。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.query_builder import RecommendationQueryBuilder

_DEFAULT_CANDIDATE_COUNT = 5
_MIN_CANDIDATE_COUNT = 1
_MAX_CANDIDATE_COUNT = 10


class RecommendationExecutor(Protocol):
    async def execute(self, query: str, *, retmax: int) -> tuple[list[CitationItem], int]: ...


@dataclass(frozen=True)
class RecommendationEvidenceResult:
    """仅由检索结果构成的推荐证据集。"""

    query: str
    boolean_query: str
    total_count: int
    items: list[CitationItem]
    warnings: list[str]


class RecommendationEvidenceService:
    """执行代码检索和最低质量门槛，不让LLM参与集合决定。"""

    def __init__(
        self,
        *,
        executor: RecommendationExecutor,
        query_builder: RecommendationQueryBuilder | None = None,
    ) -> None:
        self._executor = executor
        self._query_builder = query_builder or RecommendationQueryBuilder()

    async def search(
        self, query: str, *, candidate_count: int = _DEFAULT_CANDIDATE_COUNT
    ) -> RecommendationEvidenceResult:
        if not _MIN_CANDIDATE_COUNT <= candidate_count <= _MAX_CANDIDATE_COUNT:
            raise ValueError("candidate_count must be between 1 and 10")
        built = self._query_builder.build(query)
        raw_items, total_count = await self._executor.execute(
            built.boolean_query, retmax=max(candidate_count, _DEFAULT_CANDIDATE_COUNT)
        )
        usable = [item for item in raw_items if item.has_abstract and not item.withdrawn]
        usable.sort(key=lambda item: item.year or 0, reverse=True)
        items = usable[:candidate_count]
        warnings = [] if items else ["未找到可验证文献"]
        return RecommendationEvidenceResult(
            query=query,
            boolean_query=built.boolean_query,
            total_count=total_count,
            items=items,
            warnings=warnings,
        )
