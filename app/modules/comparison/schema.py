"""Validation and transport structures for comparison matrices."""

from datetime import datetime

from pydantic import BaseModel, Field, model_validator

from app.modules.comparison.shared import (
    DEFAULT_FIELDS,
    CellStatus,
    ComparisonField,
    SourceRef,
)

MIN_DOCUMENTS = 3
MAX_DOCUMENTS = 10

COMPARISON_FIELDS = DEFAULT_FIELDS


class ComparisonCreate(BaseModel):
    selected_document_ids: list[int] = Field(
        min_length=MIN_DOCUMENTS, max_length=MAX_DOCUMENTS
    )

    @model_validator(mode="after")
    def unique_documents(self) -> "ComparisonCreate":
        if len(set(self.selected_document_ids)) != len(self.selected_document_ids):
            raise ValueError("Document IDs must be unique")
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
