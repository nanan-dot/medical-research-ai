"""Version-pinned selection descriptors and bounded public responses."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_FRAGMENTS = 256
MAX_CHARACTERS = 8000
MAX_PAGE_SPAN = 5


class SelectionRect(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    left: float = Field(ge=0, le=1)
    top: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def inside_page(self) -> "SelectionRect":
        if self.left + self.width > 1.000000001 or self.top + self.height > 1.000000001:
            raise ValueError("rectangle exceeds page")
        return self


class SelectionFragment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_number: int = Field(ge=1, strict=True)
    start_item_index: int = Field(ge=0, strict=True)
    start_offset_utf16: int = Field(ge=0, strict=True)
    end_item_index: int = Field(ge=0, strict=True)
    end_offset_utf16: int = Field(ge=0, strict=True)
    rectangles: list[SelectionRect] = Field(default_factory=list, max_length=100)


class SelectionVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_file_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    expected_anchor_revision_id: int = Field(gt=0)
    expected_segmentation_revision_id: int = Field(gt=0)


class SourceAnchorDescriptor(SelectionVersion):
    expected_anchor_revision_id: int = Field(gt=0, strict=True)
    expected_segmentation_revision_id: int = Field(gt=0, strict=True)
    browser_quote: str = Field(min_length=1, max_length=MAX_CHARACTERS)
    fragments: list[SelectionFragment] = Field(min_length=1, max_length=MAX_FRAGMENTS)


class AnchorReference(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_anchor_id: int | None = Field(default=None, gt=0)
    anchor_descriptor: SourceAnchorDescriptor | None = None

    @model_validator(mode="after")
    def require_one_reference(self) -> "AnchorReference":
        if (self.source_anchor_id is None) == (self.anchor_descriptor is None):
            raise ValueError("provide source_anchor_id XOR anchor_descriptor")
        return self


class AnchorRead(BaseModel):
    id: int
    document_id: int
    anchor_revision_id: int
    file_hash: str
    extraction_fingerprint: str | None
    quote: str
    quote_hash: str
    resolution_status: Literal["exact", "unresolved"]
    quality_status: Literal["eligible", "review_required"]
    fragments: list[SelectionFragment]
    segment_ids: list[int]
    created_at: datetime


class ReadingNoteCreate(AnchorReference):
    content: str = Field(min_length=1, max_length=8000)

    @model_validator(mode="after")
    def nonblank_content(self) -> "ReadingNoteCreate":
        if not self.content.strip():
            raise ValueError("note content must not be blank")
        return self


class ReadingNoteRead(BaseModel):
    id: int
    source_anchor_id: int
    resolved_source_anchor_id: int | None = None
    content: str
    quote: str
    created_at: datetime


class SelectionItemRead(BaseModel):
    item_index: int
    source_array_index: int
    text: str
    rank: int | None
    eligibility: str


class SelectionPageRead(BaseModel):
    page_number: int
    rotation: int
    anchor_revision_id: int
    segmentation_revision_id: int
    pdfjs_version: str
    items: list[SelectionItemRead]
