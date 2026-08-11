"""Transport contracts for the research-context aggregate."""

from datetime import datetime

from pydantic import BaseModel, Field


class ResearchContextCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)


class ResearchContextUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)


class ResearchContextDocumentAdd(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=100)


class ResearchContextRead(BaseModel):
    id: int
    name: str
    description: str
    document_ids: list[int] = Field(default_factory=list)
    conversation_ids: list[int] = Field(default_factory=list)
    evidence_matrix_ids: list[int] = Field(default_factory=list)
    writing_project_ids: list[int] = Field(default_factory=list)
    literature_search_task_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
