"""Pydantic v2 transport contracts for the note library."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ActorScope = str
SourceType = Literal["document", "paper", "anchor"]
NoteListView = Literal["all", "recent", "favorite", "unlinked_research", "archived"]


class SourceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_type: SourceType
    source_id: int | None = Field(default=None, gt=0)
    source_version: str | None = Field(default=None, max_length=128)
    document_id: int | None = Field(default=None, gt=0)
    anchor_id: int | None = Field(default=None, gt=0)
    quote: str | None = Field(default=None, max_length=50_000)
    title: str = Field(default="", max_length=500)
    url: str | None = Field(default=None, max_length=2048)

    @model_validator(mode="after")
    def validate_identity(self) -> "SourceInput":
        if self.source_type == "anchor" and self.anchor_id is None:
            raise ValueError("anchor_id is required for anchor sources")
        if (
            self.source_type != "anchor"
            and self.source_id is None
            and self.document_id is None
        ):
            raise ValueError("source_id or document_id is required")
        return self


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_scope: ActorScope = Field(min_length=1, max_length=128)
    title: str = Field(default="", max_length=200)
    body: str = Field(default="", max_length=50_000)
    sources: list[SourceInput] = Field(default_factory=list, max_length=100)


class DraftUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_scope: ActorScope = Field(min_length=1, max_length=128)
    expected_draft_version: int = Field(ge=1)
    title: str = Field(max_length=200)
    body: str = Field(max_length=50_000)
    sources: list[SourceInput] = Field(default_factory=list, max_length=100)


class RevisionCommit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_scope: ActorScope = Field(min_length=1, max_length=128)
    expected_base_revision: int = Field(ge=0)
    expected_draft_version: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=128)


class RestoreRequest(BaseModel):
    actor_scope: ActorScope = Field(min_length=1, max_length=128)
    revision_no: int = Field(gt=0)
    expected_base_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=128)


class MetadataPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    actor_scope: ActorScope = Field(min_length=1, max_length=128)
    expected_metadata_version: int = Field(gt=0)
    is_favorite: bool | None = None
    tags: list[str] | None = Field(default=None, max_length=100)
    research_context_ids: list[int] | None = Field(default=None, max_length=100)

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 100 for value in cleaned):
            raise ValueError("tags must be nonblank and at most 100 characters")
        return cleaned


class ActorRequest(BaseModel):
    actor_scope: ActorScope = Field(min_length=1, max_length=128)


class AISuggestionCreate(ActorRequest):
    operation: Literal["organize", "polish", "title"]
    input_revision: int | None = Field(default=None, ge=0)
    input_draft_version: int | None = Field(default=None, ge=1)
    cloud_consent: bool = False

    @model_validator(mode="after")
    def one_input(self) -> "AISuggestionCreate":
        if (self.input_revision is None) == (self.input_draft_version is None):
            raise ValueError("provide exactly one input version")
        return self


class AISuggestionComplete(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    body: str | None = Field(default=None, max_length=50_000)
    failed: bool = False


class AISuggestionAdopt(ActorRequest):
    expected_draft_version: int = Field(ge=1)


class DerivationCreate(ActorRequest):
    revision_no: int = Field(gt=0)
    target_type: Literal["writing", "claim", "evidence"]
    idempotency_key: str = Field(min_length=1, max_length=128)


class ExportRequest(ActorRequest):
    note_id: int = Field(gt=0)
    revision_no: int | None = Field(default=None, gt=0)
    format: Literal["markdown", "json"]


class SourceRead(BaseModel):
    id: int
    source_type: str
    source_id: int | None
    document_id: int | None
    anchor_id: int | None
    granularity: str
    status: str
    title: str
    quote: str | None
    url: str | None
    capabilities: list[str]


class DraftRead(BaseModel):
    note_id: int
    actor_scope: str
    base_revision: int
    draft_version: int
    title: str
    body: str
    sources: list[SourceInput]
    save_state: str
    updated_at: datetime


class RevisionRead(BaseModel):
    id: int
    note_id: int
    revision_no: int
    title: str
    body: str
    origin: str
    restored_from_revision: int | None
    sources: list[SourceRead] = Field(default_factory=list)
    created_at: datetime


class NoteRead(BaseModel):
    id: int
    current_revision: int
    metadata_version: int
    title: str
    body: str
    is_favorite: bool
    is_archived: bool
    tags: list[str]
    research_context_ids: list[int]
    sources: list[SourceRead]
    capabilities: list[str]
    content_updated_at: datetime
    created_at: datetime


class NoteListItem(BaseModel):
    id: int
    current_revision: int
    metadata_version: int
    title: str
    excerpt: str
    is_favorite: bool
    is_archived: bool
    tags: list[str]
    research_context_ids: list[int]
    source_count: int
    source_summaries: list["SourceSummary"] = Field(default_factory=list)
    research_context_summaries: list["ResearchContextSummary"] = Field(
        default_factory=list
    )
    content_updated_at: datetime


class NoteListRead(BaseModel):
    items: list[NoteListItem]
    total: int
    all_total: int
    page: int
    page_size: int
    query_fingerprint: str
    as_of: datetime


class SourceSummary(BaseModel):
    source_type: str
    source_id: int | None
    title: str
    status: str


class ResearchContextSummary(BaseModel):
    id: int
    name: str


class RevisionHistoryRead(BaseModel):
    items: list[RevisionRead]
    total: int
    page: int
    page_size: int


class FacetValue(BaseModel):
    id: int | str
    name: str
    count: int


class FacetsRead(BaseModel):
    tags: list[FacetValue]
    research_contexts: list[FacetValue]
    quick_counts: dict[str, int]
    query_fingerprint: str
    as_of: datetime


class AISuggestionRead(BaseModel):
    id: int
    note_id: int
    input_revision: int | None
    input_draft_version: int | None
    operation: str
    status: str
    title: str | None
    body: str | None
    is_stale: bool
    adopted_at: datetime | None


class DerivationRead(BaseModel):
    id: int
    note_id: int
    revision_id: int
    target_type: str
    status: str


class ExportRead(BaseModel):
    filename: str
    media_type: str
    content: str
    revision_no: int


class LegacyBackfillRead(BaseModel):
    dry_run: bool
    eligible: int
    created: int
    skipped: int
