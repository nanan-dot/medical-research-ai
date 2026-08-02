from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=10)
    title: str | None = Field(default=None, max_length=200)


class MessageCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class CitationRead(BaseModel):
    id: int
    evidence_type: str
    document_id: int
    page: int | None
    section: str | None
    evidence_text: str | None
    citation_text: str | None
    retrieval_score: float | None


class MessageRead(BaseModel):
    id: int
    sequence: int
    role: str
    content: str
    model_version: str | None
    latency_ms: int | None
    feedback: int | None
    created_at: datetime
    citations: list[CitationRead] = []


class ConversationRead(BaseModel):
    id: int
    document_ids: list[int]
    title: str | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=-1, le=1)
