"""论文库 HTTP 契约与稳定枚举。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class ReadingStatus(StrEnum):
    UNREAD = "unread"
    READING = "reading"
    READ = "read"


class ResearchRole(StrEnum):
    CORE_EVIDENCE = "core_evidence"
    BACKGROUND_SUPPORT = "background_support"
    METHOD_REFERENCE = "method_reference"
    SUPPLEMENTARY_READING = "supplementary_reading"
    TO_EVALUATE = "to_evaluate"


class ReadingStateUpdate(BaseModel):
    status: ReadingStatus
    progress_percent: int = Field(ge=0, le=100)
    current_section: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def validate_progress(self) -> "ReadingStateUpdate":
        if self.status is ReadingStatus.UNREAD and self.progress_percent != 0:
            raise ValueError("未阅读状态的进度必须为 0")
        if self.status is ReadingStatus.UNREAD:
            self.current_section = None
        if self.status is ReadingStatus.READ and self.progress_percent != 100:
            raise ValueError("已阅读状态的进度必须为 100")
        return self


class ReadingStateRead(BaseModel):
    reading_status: ReadingStatus
    reading_progress_percent: int
    current_section: str | None
    last_read_at: datetime | None
    last_work_kind: str | None


class ResearchRelationUpdate(BaseModel):
    role: ResearchRole | None
    note: str | None = Field(default=None, max_length=2000)
    # 允许 0 作为客户端刻意提交的过期版本，以便服务层统一返回 409 冲突。
    expected_version: int | None = Field(default=None, ge=0)


class ResearchRelationRead(BaseModel):
    research_context_id: int
    research_name: str
    role: ResearchRole | None
    note: str | None
    version: int


class ActivityRead(BaseModel):
    id: int
    kind: str
    detail: str | None
    created_at: datetime


class WorkEntryRead(BaseModel):
    action: str
    enabled: bool
    reason: str | None = None


class PaperItemRead(BaseModel):
    id: int
    pmid: str | None
    doi: str | None
    title: str | None
    authors: str | None
    journal: str | None
    year: int | None
    paper_type: str | None
    journal_quartile: str | None
    journal_quartile_source: str | None
    journal_quartile_year: int | None
    metadata_status: str
    metadata_source: str | None
    metadata_retryable: bool
    metadata_error_code: str | None
    document_id: int | None
    fulltext_status: str
    reading_status: ReadingStatus
    reading_progress_percent: int
    current_section: str | None
    analysis_status: str
    analysis_progress: dict[str, int] | None = None
    primary_relation: ResearchRelationRead | None = None
    additional_relation_count: int = 0
    recent_activity: ActivityRead | None = None
    tags: list[str] = Field(default_factory=list)
    can_read: bool
    can_analyze: bool
    capability_reason: str | None = None
    preferred_work_action: str
    last_work_at: datetime | None
    reading_entry: WorkEntryRead
    analysis_entry: WorkEntryRead


class PaperItemPage(BaseModel):
    items: list[PaperItemRead]
    total: int
    offset: int
    limit: int


class FacetValue(BaseModel):
    value: str
    count: int
    label: str | None = None


class PaperLibraryFacets(BaseModel):
    reading_status: list[FacetValue]
    analysis_status: list[FacetValue]
    paper_types: list[FacetValue]
    research_roles: list[FacetValue]
    research_contexts: list[FacetValue]
    tags: list[FacetValue]


class PaperTagsUpdate(BaseModel):
    tags: list[str] = Field(max_length=50)

    @model_validator(mode="after")
    def normalize_tags(self) -> "PaperTagsUpdate":
        normalized = list(
            dict.fromkeys(tag.strip() for tag in self.tags if tag.strip())
        )
        if any(len(tag) > 64 for tag in normalized):
            raise ValueError("单个标签不能超过 64 个字符")
        self.tags = normalized
        return self


class PaperLibrarySummary(BaseModel):
    all: int
    recent: int
    reading: int
    analyzing: int
    unclassified: int


class PaperOverviewRead(PaperItemRead):
    relations: list[ResearchRelationRead]
    activities: list[ActivityRead]


class PaperAddRequest(BaseModel):
    doi: str | None = Field(default=None, max_length=300)
    pmid: str | None = Field(default=None, max_length=20)
    document_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_verifiable_identity(self) -> "PaperAddRequest":
        if not self.doi and not self.pmid and self.document_id is None:
            raise ValueError("至少提供 DOI、PMID 或资料库文档")
        return self


class PaperAddResult(BaseModel):
    item: PaperItemRead
    outcome: str
