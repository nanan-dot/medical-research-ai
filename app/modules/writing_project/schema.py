"""写作项目的类型安全契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.comparison.shared import SourceRef

WritingType = Literal[
    "reading_note",
    "group_meeting",
    "review",
    "proposal",
    "introduction",
    "discussion",
    "abstract",
    "cover_letter",
    "reviewer_response",
]


class WritingSection(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    draft: str = ""


class PendingItem(BaseModel):
    id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    type: Literal["citation", "data", "claim"]
    status: Literal["pending", "resolved"] = "pending"
    section_id: str
    paragraph_id: str


class ModelEvent(BaseModel):
    model_name: str
    model_version: str
    generated_at: datetime
    is_cloud: bool


class GeneratedContent(BaseModel):
    sections: list[WritingSection] = Field(default_factory=list)
    citations: list[SourceRef] = Field(default_factory=list)
    pending_items: list[PendingItem] = Field(default_factory=list)
    model_events: list[ModelEvent] = Field(default_factory=list)


class WritingProjectSnapshot(BaseModel):
    version: int = Field(gt=0)
    parent_version: int | None
    content: GeneratedContent


class WritingProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    writing_type: WritingType
    generated_content: GeneratedContent = Field(default_factory=GeneratedContent)


class WritingProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    generated_content: GeneratedContent | None = None
    expected_version: int = Field(gt=0)


class UserMaterialCreate(BaseModel):
    text: str = Field(min_length=1)
    source_document_id: int | None = Field(default=None, gt=0)


class UserMaterialRead(UserMaterialCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WritingProjectRead(BaseModel):
    id: int
    name: str
    writing_type: WritingType
    generated_content: GeneratedContent
    version: int
    user_materials: list[UserMaterialRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class WritingVersionRead(WritingProjectSnapshot):
    created_at: datetime
