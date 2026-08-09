from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.comparison.shared import SourceRef


class OutlineSection(BaseModel):
    title: str
    content: str
    evidence: list[SourceRef] = Field(default_factory=list)
    missing_evidence: bool = False


class PresentationCreate(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=10)
    comparison_id: int | None = Field(default=None, gt=0)


class PresentationPatch(BaseModel):
    sections: list[OutlineSection] = Field(min_length=1)


class PresentationRead(BaseModel):
    id: int
    document_ids: list[int]
    sections: list[OutlineSection]
    version: int
    created_at: datetime
    updated_at: datetime
