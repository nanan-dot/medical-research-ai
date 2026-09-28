"""统一科研对话的公开请求与响应契约。"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.modules.conversation.schema import ReaderContext

PositiveId = Annotated[int, Field(gt=0, strict=True)]
Question = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConversationMode(str, Enum):
    AUTO = "auto"
    GENERAL = "general"
    EVIDENCE_ONLY = "evidence_only"


class AnswerMode(str, Enum):
    GENERAL = "general"
    PAPER_GROUNDED = "paper_grounded"
    MIXED = "mixed"
    WEB_AUGMENTED = "web_augmented"


class UnifiedConversationCreate(StrictRequest):
    document_ids: list[PositiveId] = Field(default_factory=list, max_length=10)
    title: str | None = Field(default=None, max_length=200)
    research_context_id: int | None = Field(default=None, gt=0)


class UnifiedMessageCreate(StrictRequest):
    message: Question
    mode: ConversationMode = ConversationMode.AUTO
    allow_general_supplement: bool = False
    allow_web_search: bool = False
    web_query: str | None = Field(default=None, min_length=1, max_length=500)
    document_ids: list[PositiveId] | None = Field(default=None, max_length=10)
    scope_type: Literal["selected_documents", "library"] = "selected_documents"
    reader_context: ReaderContext | None = None
    request_id: str = Field(
        default_factory=lambda: uuid4().hex,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )


class UnifiedCitationRead(BaseModel):
    document_id: int | None = None
    page: int | None = None
    section: str | None = None
    evidence_text: str | None = None
    citation_text: str | None = None
    source_anchor_id: int | None = None
    anchor_status: str = "legacy_unversioned"
    url: str | None = None
    pmid: str | None = None
    source_level: Literal["paper_excerpt", "metadata", "abstract"] = "paper_excerpt"


class UnifiedAnswerSection(BaseModel):
    source_type: str
    content: str
    citations: list[UnifiedCitationRead] = Field(default_factory=list)
    answer_status: str = "answered"


class UnifiedMessageRead(BaseModel):
    id: int
    sequence: int
    role: str
    content: str
    source_type: str
    answer_status: str | None
    created_at: datetime
    sections: list[UnifiedAnswerSection] = Field(default_factory=list)
    citations: list[UnifiedCitationRead] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UnifiedConversationRead(BaseModel):
    id: int
    document_ids: list[int]
    title: str | None
    research_context_id: int | None
    messages: list[UnifiedMessageRead]


class UnifiedAnswerRead(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    answer_mode: AnswerMode
    answer_status: str
    route_reason_code: str
    scope_used: list[int]
    citations: list[UnifiedCitationRead] = Field(default_factory=list)
    sections: list[UnifiedAnswerSection] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    trace_id: str = Field(default_factory=lambda: uuid4().hex)
    request_id: str = ""
    latency_ms: int = 0


class AnswerContent(BaseModel):
    """执行器只返回答案数据；消息写入由统一服务负责。"""

    sections: list[UnifiedAnswerSection] = Field(default_factory=list)
    status: str = "answered"
    warnings: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)
    model_version: str | None = None
    scope_used: list[int] = Field(default_factory=list)


class GapRead(BaseModel):
    id: int
    question: str
    document_ids: list[int]
    research_context_id: int | None
    occurrences: int
