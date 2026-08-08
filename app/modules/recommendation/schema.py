"""推荐 API 的稳定输入输出契约。"""

from typing import Literal

from pydantic import BaseModel, Field

from app.modules.literature_search.schema import CitationItem

RecommendationStatus = Literal["completed", "completed_with_warnings", "unavailable"]


class RecommendationRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    candidate_count: int = Field(default=5, ge=1, le=10)


class RecommendationItem(BaseModel):
    citation: CitationItem
    recommendation_reason: str = Field(min_length=1)


class RecommendationResponse(BaseModel):
    query: str
    status: RecommendationStatus
    items: list[RecommendationItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
