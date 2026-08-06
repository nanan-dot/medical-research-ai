"""Validation and transport structures for comparison matrices."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator

MIN_DOCUMENTS = 3
MAX_DOCUMENTS = 10
MISSING_VALUE = "缺失"


class ComparisonField(StrEnum):
    STUDY_TYPE = "study_type"
    STUDY_POPULATION = "study_population"
    SAMPLE_SIZE = "sample_size"
    INTERVENTION = "intervention"
    COMPARATOR = "comparator"
    OUTCOME = "outcome"
    METHODS = "methods"
    STATISTICS = "statistics"
    RESULTS = "results"
    NOVELTY = "novelty"
    LIMITATIONS = "limitations"
    SOURCE = "source"


COMPARISON_FIELDS = tuple(ComparisonField)


class CellStatus(StrEnum):
    GENERATED = "generated"
    USER_EDITED = "user_edited"
    MISSING = "missing"


class SourceRef(BaseModel):
    pmid: str | None = Field(default=None, pattern=r"^\d{1,20}$")
    doi: str | None = Field(default=None, pattern=r"^10\.\d{4,9}/\S+$")
    locator: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def require_identifier(self) -> "SourceRef":
        if self.pmid is None and self.doi is None:
            raise ValueError("Source requires PMID or DOI")
        return self


class ComparisonCreate(BaseModel):
    selected_document_ids: list[int] = Field(min_length=MIN_DOCUMENTS, max_length=MAX_DOCUMENTS)

    @model_validator(mode="after")
    def unique_documents(self) -> "ComparisonCreate":
        if len(set(self.selected_document_ids)) != len(self.selected_document_ids):
            raise ValueError("Document IDs must be unique")
        return self


class ComparisonCellGenerated(BaseModel):
    document_id: int
    field: ComparisonField
    generated_value: str | None = None
    sources: list[SourceRef] = Field(default_factory=list)
    cell_value: str = MISSING_VALUE
    status: CellStatus = CellStatus.MISSING

    @model_validator(mode="after")
    def enforce_evidence(self) -> "ComparisonCellGenerated":
        if self.generated_value and self.sources:
            self.cell_value = self.generated_value
            self.status = CellStatus.GENERATED
        return self


class ComparisonCellEdit(BaseModel):
    document_id: int = Field(gt=0)
    field: ComparisonField
    user_value: str = Field(min_length=1, max_length=4000)


class ComparisonCellRead(BaseModel):
    document_id: int
    field: ComparisonField
    cell_value: str
    sources: list[SourceRef]
    generated_value: str | None
    user_value: str | None
    status: CellStatus


class ComparisonTaskRead(BaseModel):
    id: int
    selected_document_ids: list[int]
    fields: list[ComparisonField]
    status: str
    created_at: datetime
    cells: list[ComparisonCellRead]
