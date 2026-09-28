"""Stable API structures for evidence-grounded paper analysis."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.integrations.paperqa2 import PaperSource


class AnalysisStatus(StrEnum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ClaimKind(StrEnum):
    FACT = "fact"
    SUMMARY = "summary"
    INFERENCE = "inference"
    NOT_FOUND = "not_found"


class AnalysisField(BaseModel):
    value: str = Field(min_length=1, max_length=4000)
    kind: ClaimKind
    source_indices: list[int] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def evidence_rules(self):
        if self.kind == ClaimKind.NOT_FOUND:
            self.value = "未找到"
            self.source_indices = []
        return self


class StructuredPaperResult(BaseModel):
    basic_information: AnalysisField
    one_sentence_conclusion: AnalysisField
    research_background: AnalysisField
    research_question: AnalysisField
    study_type: AnalysisField
    population: AnalysisField
    sample_size: AnalysisField
    intervention_or_exposure: AnalysisField
    comparator: AnalysisField
    primary_outcome: AnalysisField
    statistical_methods: AnalysisField
    main_results: AnalysisField
    innovations: AnalysisField
    limitations: AnalysisField
    next_questions: AnalysisField
    original_evidence: AnalysisField
    pending_items: AnalysisField


class PaperAnalysisCreate(BaseModel):
    document_id: int = Field(gt=0)


class PaperAnalysisCorrection(BaseModel):
    field_name: str = Field(min_length=1, max_length=64)
    value: str = Field(min_length=1, max_length=4000)
    kind: ClaimKind = ClaimKind.SUMMARY
    source_indices: list[int] = Field(default_factory=list, max_length=10)


class PaperAnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    analysis_status: AnalysisStatus
    template_version: str
    model_version: str
    generation: int
    task_set_version: str | None
    task_names: list[str]
    completed_task_names: list[str]
    structured_result: StructuredPaperResult | None
    sources: list[PaperSource]
    pending_confirmations: list[str]
    error_code: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
