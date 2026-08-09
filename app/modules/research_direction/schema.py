"""候选研究方向的输入、输出与模型生成契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.comparison.shared import SourceRef

GenerationStrategy = Literal["gap-based", "cross-topic"]
Priority = Literal["high", "medium", "low"]
DETAIL_FIELDS = (
    "methods",
    "requirements",
    "difficulty",
    "time_risk",
    "resource_risk",
    "ethics_risk",
    "search_terms",
    "advisor_questions",
)
FORBIDDEN_CLAIMS = (
    "保证发表",
    "一定能",
    "最前沿",
    "首次",
    "首创",
    "空白领域",
    "没人做过",
)


class EvidenceStatement(BaseModel):
    statement: str = Field(min_length=1, max_length=1200)
    source: SourceRef


class GroundedText(BaseModel):
    """需要给导师讨论的陈述与其可追溯证据。"""

    text: str = Field(min_length=1, max_length=2000)
    sources: list[SourceRef] = Field(min_length=1, max_length=20)


class CandidateCore(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    question: str = Field(min_length=1, max_length=2000)
    research_object: str = Field(min_length=1, max_length=2000)
    study_type: str = Field(min_length=1, max_length=100)
    evidence: list[EvidenceStatement] = Field(min_length=1, max_length=20)
    current_evidence: GroundedText
    controversy: GroundedText
    gap: str = Field(min_length=1, max_length=2000)
    novelty_uncertainty: str = Field(min_length=1, max_length=1200)
    priority: Priority
    generation_strategy: GenerationStrategy
    missing_evidence: bool = False

    @model_validator(mode="after")
    def prevent_overclaiming(self) -> "CandidateCore":
        content = " ".join(
            (
                self.name,
                self.question,
                self.current_evidence.text,
                self.controversy.text,
                self.gap,
            )
        )
        if any(word in content for word in FORBIDDEN_CLAIMS):
            raise ValueError("Candidate contains prohibited overclaiming language")
        if "当前检索结果中较少见" not in self.gap:
            raise ValueError("Gap must use conservative retrieval-result wording")
        return self


class DirectionDetails(BaseModel):
    methods: str = Field(min_length=1, max_length=2000)
    requirements: str = Field(min_length=1, max_length=2000)
    difficulty: str = Field(min_length=1, max_length=1000)
    time_risk: str = Field(min_length=1, max_length=1000)
    resource_risk: str = Field(min_length=1, max_length=1000)
    ethics_risk: str = Field(min_length=1, max_length=1000)
    search_terms: str = Field(min_length=3, max_length=2000)
    advisor_questions: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_search_terms(self) -> "DirectionDetails":
        if "[Title/Abstract]" not in self.search_terms:
            raise ValueError("Search terms must be executable PubMed Boolean fragments")
        return self


class GenerationMetadata(BaseModel):
    model_version: str = Field(min_length=1, max_length=200)
    input_conditions_version: int = Field(ge=1)
    evidence_matrix_version: int = Field(ge=1)
    strategy: GenerationStrategy
    generated_at: datetime


class ResearchDirectionGenerateRequest(BaseModel):
    research_conditions_id: int = Field(gt=0)
    evidence_matrix_id: int = Field(gt=0)
    model_config_id: int | None = Field(default=None, ge=1)
    candidate_count: int = Field(default=3, ge=3, le=8)


class ResearchDirectionPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=300)
    question: str | None = Field(default=None, min_length=1, max_length=2000)
    research_object: str | None = Field(default=None, min_length=1, max_length=2000)
    study_type: str | None = Field(default=None, min_length=1, max_length=100)
    controversy: GroundedText | None = None
    gap: str | None = Field(default=None, min_length=1, max_length=2000)
    novelty_uncertainty: str | None = Field(default=None, min_length=1, max_length=1200)
    priority: Priority | None = None
    merge_source_ids: list[int] | None = Field(
        default=None, min_length=1, max_length=20
    )


class ResearchDirectionRead(CandidateCore):
    model_config = ConfigDict(from_attributes=True)

    id: int
    research_conditions_id: int
    evidence_matrix_id: int
    metadata: GenerationMetadata
    methods: str | None = None
    requirements: str | None = None
    difficulty: str | None = None
    time_risk: str | None = None
    resource_risk: str | None = None
    ethics_risk: str | None = None
    search_terms: str | None = None
    advisor_questions: str | None = None
    merged_from_ids: list[int] = Field(default_factory=list)
    status: Literal["active", "merged", "accepted", "rejected"]
    merged_into_id: int | None = None
    version: int
    created_at: datetime
    updated_at: datetime
