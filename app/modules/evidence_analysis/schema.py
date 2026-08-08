"""Request and response contracts for two-tier evidence analysis."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.comparison.shared import SourceRef

Trend = Literal["up", "flat", "down", "insufficient"]
Confidence = Literal["high", "medium", "low"]


class EvidenceAnalysisRequest(BaseModel):
    matrix_id: int = Field(gt=0)
    retrieval_scope: str = Field(min_length=1, max_length=2000)
    retrieval_date: date = Field(default_factory=date.today)
    model_config_id: int | None = Field(default=None, ge=1)
    topic_field_keys: list[str] = Field(
        default_factory=lambda: ["intervention", "outcome"], min_length=1, max_length=10
    )


class AnalysisMetadata(BaseModel):
    retrieval_scope: str
    retrieval_date: date
    matrix_version: int
    document_count: int


class TopicStatisticRead(BaseModel):
    topic: str
    count: int
    year_range: str | None
    trend: Trend
    basis: str
    research_types: dict[str, int]


class ResearchTypeStatisticRead(BaseModel):
    research_type: str
    count: int
    basis: str


class StatisticsLayerRead(BaseModel):
    high_frequency_topics: list[TopicStatisticRead]
    recent_growth_topics: list[TopicStatisticRead]
    research_type_distribution: list[ResearchTypeStatisticRead]


class InterpretationItem(BaseModel):
    statement: str = Field(min_length=1, max_length=1200)
    confidence: Confidence
    evidence: list[SourceRef] = Field(min_length=1, max_length=20)
    statistics_basis: list[str] = Field(min_length=1, max_length=10)
    research_types: list[str] = Field(min_length=1, max_length=10)


class ConflictInterpretationItem(InterpretationItem):
    conflicting_point: str = Field(min_length=1, max_length=800)
    supporting_evidence: list[SourceRef] = Field(min_length=1, max_length=20)
    opposing_evidence: list[SourceRef] = Field(min_length=1, max_length=20)


class SearchQuestionItem(InterpretationItem):
    question: str = Field(min_length=1, max_length=500)
    search_fragment: str = Field(min_length=3, max_length=1000)


class InterpretationLayerRead(BaseModel):
    consistencies: list[InterpretationItem] = Field(default_factory=list)
    conflicts: list[ConflictInterpretationItem] = Field(default_factory=list)
    limitations: list[InterpretationItem] = Field(default_factory=list)
    gaps: list[InterpretationItem] = Field(default_factory=list)
    search_questions: list[SearchQuestionItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def prevent_overclaiming(self) -> "InterpretationLayerRead":
        forbidden_words = ("没人做过", "空白领域", "首次")
        all_items = [*self.consistencies, *self.conflicts, *self.limitations, *self.gaps, *self.search_questions]
        for item in all_items:
            if any(word in item.statement for word in forbidden_words):
                raise ValueError("Interpretation contains prohibited overclaiming language")
        return self


class EvidenceAnalysisRead(BaseModel):
    metadata: AnalysisMetadata
    statistics: StatisticsLayerRead
    interpretation: InterpretationLayerRead
