from enum import StrEnum
from pydantic import BaseModel, Field


class ExportType(StrEnum):
    ANALYSIS = "analysis"
    CONVERSATION = "conversation"


class MarkdownExportCreate(BaseModel):
    export_type: ExportType
    source_id: int = Field(gt=0)
    filename: str = Field(default="研究记录", min_length=1, max_length=100)
    user_notes: str | None = Field(default=None, max_length=10000)


class ExportRead(BaseModel):
    id: int
    export_type: ExportType
    source_ids: list[int]
    generated_at: str
    model_info: str | None
    pending_confirmations: list[str]
    filename: str
