"""PDF 批注 API 契约与输入边界校验。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator

_FILE_HASH_PATTERN = r"^[a-f0-9]{64}$"
_GEOMETRY_TOLERANCE = 1e-9


class AnnotationColor(StrEnum):
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PINK = "pink"


class AnnotationVersionStatus(StrEnum):
    CURRENT = "current"
    RELOCATION_REQUIRED = "relocation_required"


class AnnotationRect(BaseModel):
    """相对于页面宽高的选区矩形，消除不同缩放比例的坐标歧义。"""

    left: float = Field(ge=0, le=1)
    top: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def ensure_rect_stays_inside_page(self) -> "AnnotationRect":
        if self.left + self.width > 1 + _GEOMETRY_TOLERANCE:
            raise ValueError("selection rectangle exceeds page width")
        if self.top + self.height > 1 + _GEOMETRY_TOLERANCE:
            raise ValueError("selection rectangle exceeds page height")
        return self


class AnnotationCreate(BaseModel):
    expected_file_hash: str = Field(pattern=_FILE_HASH_PATTERN)
    page_number: int = Field(ge=1)
    rectangles: list[AnnotationRect] = Field(min_length=1, max_length=100)
    selected_text: str = Field(min_length=1, max_length=4000)
    color: AnnotationColor = AnnotationColor.YELLOW
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("expected_file_hash")
    @classmethod
    def normalize_file_hash(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("selected_text")
    @classmethod
    def normalize_selected_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("selected text must not be blank")
        return normalized

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None


class AnnotationUpdate(BaseModel):
    expected_file_hash: str = Field(pattern=_FILE_HASH_PATTERN)
    color: AnnotationColor | None = None
    note: str | None = Field(default=None, max_length=2000)

    @field_validator("expected_file_hash")
    @classmethod
    def normalize_file_hash(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @model_validator(mode="after")
    def require_mutable_field(self) -> "AnnotationUpdate":
        if not self.model_fields_set.intersection({"color", "note"}):
            raise ValueError("at least one mutable annotation field is required")
        return self


class AnnotationRead(BaseModel):
    id: int
    document_id: int
    file_hash: str
    page_number: int
    rectangles: list[AnnotationRect]
    selected_text: str
    selected_text_hash: str
    color: AnnotationColor
    note: str | None
    version_status: AnnotationVersionStatus
    created_at: datetime
    updated_at: datetime
