from datetime import datetime

from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=10)
    title: str | None = Field(default=None, max_length=200)
    research_context_id: int | None = Field(default=None, gt=0)


class MessageCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_id: int | None = Field(default=None, gt=0)
    source_anchor_id: int | None = Field(default=None, gt=0)
    active_segment_id: int | None = Field(default=None, gt=0)
    section_id: int | None = Field(default=None, gt=0)
    expected_anchor_revision_id: int | None = Field(default=None, gt=0)
    expected_segmentation_revision_id: int | None = Field(default=None, gt=0)

    def reader_context(self) -> "ReaderContext | None":
        """Return an explicit persisted context only when the reader supplied one."""
        values = self.model_dump(exclude={"question"}, exclude_none=True)
        return ReaderContext(**values) if values else None


class ReaderContext(BaseModel):
    document_id: int
    source_anchor_id: int | None = None
    active_segment_id: int | None = None
    section_id: int | None = None
    expected_anchor_revision_id: int
    expected_segmentation_revision_id: int | None = None


class CitationRead(BaseModel):
    id: int
    source_anchor_id: int | None = None
    anchor_status: str = "legacy_unversioned"
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
    answer_status: str | None
    uncertainty: float | None
    reason_codes: list[str]
    created_at: datetime
    citations: list[CitationRead] = []


class ConversationRead(BaseModel):
    id: int
    document_ids: list[int]
    title: str | None
    research_context_id: int | None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageRead]


class ConversationSummary(BaseModel):
    id: int
    document_ids: list[int]
    title: str | None
    research_context_id: int | None
    updated_at: datetime
    message_count: int


class FeedbackCreate(BaseModel):
    rating: int = Field(ge=-1, le=1)
