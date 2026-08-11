"""API contracts for the paper-research workspace."""

from datetime import datetime

from pydantic import BaseModel, Field


class IndexedDocumentRead(BaseModel):
    document_id: int
    title: str
    year: int | None
    pmid: str | None


class IndexedDocumentPage(BaseModel):
    items: list[IndexedDocumentRead]
    total: int
    offset: int
    limit: int


class RecentAnalysisRead(BaseModel):
    analysis_id: int
    document_id: int
    title: str
    updated_at: datetime


class PendingConfirmationRead(BaseModel):
    analysis_id: int
    document_id: int
    title: str
    field_name: str
    updated_at: datetime


class RecentConversationRead(BaseModel):
    id: int
    document_ids: list[int]
    title: str | None
    updated_at: datetime
    message_count: int = Field(ge=0)


class PaperResearchOverviewRead(BaseModel):
    recent_analyses: list[RecentAnalysisRead]
    pending_confirmations: list[PendingConfirmationRead]
    recent_conversations: list[RecentConversationRead]
