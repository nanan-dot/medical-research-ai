"""Validation and transport structures for evidence matrices."""

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.modules.comparison.schema import SourceRef

# 论文数量边界：与 WP11 保持一致（3-10 篇）。
MIN_DOCUMENTS = 3
MAX_DOCUMENTS = 10
# 缺失值的显式展示（review-paper 融合：绝不编造缺失数据）。
MISSING_VALUE = "缺失"
# 备注与相关度字段长度上限。
MAX_NOTES_LENGTH = 2000


class ReadingStatus(StrEnum):
    UNREAD = "unread"
    READING = "reading"
    READ = "read"


class DocumentStatus(StrEnum):
    INCLUDED = "included"
    PENDING = "pending"


class TopicRelevance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MatrixStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class CellStatus(StrEnum):
    GENERATED = "generated"
    USER_EDITED = "user_edited"
    MISSING = "missing"


class SourceType(StrEnum):
    PUBMED = "pubmed"
    DOI = "doi"
    MANUAL = "manual"


class MatrixCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    # 预置字段（可选）：不传则使用默认比较字段集。
    fields: list[str] | None = Field(default=None, min_length=1, max_length=50)
    # 可选：基于 comparison task 创建（复用其字段与已选文献）。
    source_comparison_id: int | None = Field(default=None, ge=1)
    research_context_id: int | None = Field(default=None, ge=1)


class MatrixUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    status: MatrixStatus | None = None
    research_context_id: int | None = Field(default=None, ge=1)


class MatrixDocumentAdd(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=MAX_DOCUMENTS)

    @model_validator(mode="after")
    def unique_documents(self) -> "MatrixDocumentAdd":
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("Document IDs must be unique")
        return self


class MatrixDocumentRemove(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=MAX_DOCUMENTS)


class MatrixDocumentUpdate(BaseModel):
    user_notes: str | None = Field(default=None, max_length=MAX_NOTES_LENGTH)
    topic_relevance: TopicRelevance | None = None
    reading_status: ReadingStatus | None = None
    document_status: DocumentStatus | None = None


class MatrixFieldAdd(BaseModel):
    field_key: str = Field(min_length=1, max_length=64)
    field_label: str = Field(min_length=1, max_length=200)


class MatrixCellEdit(BaseModel):
    document_id: int = Field(gt=0)
    field_key: str = Field(min_length=1, max_length=64)
    user_value: str = Field(min_length=1, max_length=4000)


class MatrixCellGenerated(BaseModel):
    document_id: int
    field_key: str
    generated_value: str | None = None
    # 来源可能由 manual 用户自填：provenance=manual 区别于模型生成。
    sources: list[SourceRef] = Field(default_factory=list)
    provenance: Literal["model", "manual"] = "model"
    cell_value: str = MISSING_VALUE
    status: CellStatus = CellStatus.MISSING

    @model_validator(mode="after")
    def enforce_evidence(self) -> "MatrixCellGenerated":
        # 无来源的值不得标记为 generated（verify-refs：缺失显式标注）。
        if self.generated_value and self.sources:
            self.cell_value = self.generated_value
            self.status = CellStatus.GENERATED
        return self


# 导出格式（复用 comparison 命名，供 Query 与响应复用）。
MatrixExportFormat = Literal["csv", "markdown"]


class MatrixDocumentRead(BaseModel):
    id: int
    matrix_id: int
    document_id: int
    user_notes: str
    topic_relevance: TopicRelevance
    reading_status: ReadingStatus
    document_status: DocumentStatus
    added_at: datetime


class MatrixFieldRead(BaseModel):
    id: int
    matrix_id: int
    field_key: str
    field_label: str
    position: int
    active: bool


class MatrixCellRead(BaseModel):
    id: int
    matrix_id: int
    document_id: int
    field_key: str
    cell_value: str
    sources: list[SourceRef]
    generated_value: str | None
    user_value: str | None
    status: CellStatus


class EvidenceMatrixRead(BaseModel):
    id: int
    name: str
    description: str
    status: MatrixStatus
    version: int
    source_comparison_id: int | None
    research_context_id: int | None
    created_at: datetime
    updated_at: datetime
    # 只含 active 字段（停用字段不展示，历史单元格数据仍在库中）。
    fields: list[MatrixFieldRead]
    documents: list[MatrixDocumentRead]
    cells: list[MatrixCellRead]


class EvidenceMatrixList(BaseModel):
    items: list[EvidenceMatrixRead]
    total: int


class ExportRequest(BaseModel):
    format: MatrixExportFormat = "markdown"
