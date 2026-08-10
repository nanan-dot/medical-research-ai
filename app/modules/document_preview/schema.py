"""文档只读预览接口模型。"""

from enum import StrEnum

from pydantic import BaseModel, Field


class DocumentPreviewKind(StrEnum):
    PDF = "pdf"
    DOCX = "docx"
    UNAVAILABLE = "unavailable"


class DocumentPreviewBlockKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"


class DocumentPreviewBlock(BaseModel):
    """DOCX 的受控结构化文本块，前端必须以插值而非 HTML 注入渲染。"""

    kind: DocumentPreviewBlockKind
    text: str = Field(max_length=10000)
    level: int | None = Field(default=None, ge=1, le=9)


class DocumentPreviewTable(BaseModel):
    """DOCX 表格的只读单元格值。"""

    rows: list[list[str]] = Field(default_factory=list, max_length=200)


class DocumentPreviewRead(BaseModel):
    document_id: int
    kind: DocumentPreviewKind
    content_url: str | None = None
    blocks: list[DocumentPreviewBlock] = Field(default_factory=list, max_length=2000)
    tables: list[DocumentPreviewTable] = Field(default_factory=list, max_length=100)
    message: str | None = None
