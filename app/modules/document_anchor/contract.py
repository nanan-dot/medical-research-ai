"""不信任子进程：每页验证结构、身份与内容哈希，只有完整流可发布。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.modules.document_anchor.fingerprint import document_content_hash, record_hash
from app.modules.document_anchor.normalization import utf16_length
from app.modules.document_anchor.toolchain import identity

MAX_TEXT_ITEM_CHARACTERS = 20_000


class ContractValidationError(ValueError):
    """Safe protocol failure without embedding source text."""


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class HeaderRecord(Record):
    record_type: Literal["header"] = "header"
    contract_schema_version: str
    request_id: str = Field(min_length=1, max_length=128)
    extractor_version: str = Field(min_length=1, max_length=64)
    pdfjs_version: str = Field(min_length=1, max_length=64)
    normalization_version: str = Field(min_length=1, max_length=64)
    file_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    options_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_count: int = Field(ge=1, le=500, strict=True)


class TextItemRecord(Record):
    item_index: int = Field(ge=0, strict=True)
    source_array_index: int = Field(ge=0, strict=True)
    text: str = Field(max_length=MAX_TEXT_ITEM_CHARACTERS)
    direction: Literal["ltr", "rtl", "ttb"]
    transform: tuple[float, float, float, float, float, float]
    width: float = Field(ge=0)
    height: float = Field(ge=0)
    font_name: str | None = Field(default=None, max_length=256)
    has_eol: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_unicode(self) -> TextItemRecord:
        if utf16_length(self.text) > MAX_TEXT_ITEM_CHARACTERS:
            raise ValueError("TextItem UTF16 limit")
        if self.font_name:
            utf16_length(self.font_name)
        return self


class FontStyle(Record):
    font_family: str = Field(max_length=256)
    ascent: float | None = None
    descent: float | None = None
    vertical: bool


class PageRecord(Record):
    record_type: Literal["page"] = "page"
    page_number: int = Field(ge=1, le=500, strict=True)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    rotation: Literal[0, 90, 180, 270]
    view_box: tuple[float, float, float, float]
    items: list[TextItemRecord] = Field(max_length=50_000)
    styles: dict[str, FontStyle] = Field(default_factory=dict, max_length=4096)
    has_raster_image: bool = False
    page_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_page_structure(self) -> PageRecord:
        if self.view_box[2] <= self.view_box[0] or self.view_box[3] <= self.view_box[1]:
            raise ValueError("Invalid page view box")
        if [item.item_index for item in self.items] != list(range(len(self.items))):
            raise ValueError("TextItem indexes must be contiguous")
        source_indexes = [item.source_array_index for item in self.items]
        if source_indexes != sorted(set(source_indexes)):
            raise ValueError("TextItem source indexes must strictly increase")
        for key, style in self.styles.items():
            if utf16_length(key) > 256 or utf16_length(style.font_family) > 256:
                raise ValueError("Invalid style metadata")
        return self


class TrailerRecord(Record):
    record_type: Literal["trailer"] = "trailer"
    request_id: str = Field(min_length=1, max_length=128)
    pages_emitted: int = Field(ge=0, le=500, strict=True)
    items_emitted: int = Field(ge=0, strict=True)
    document_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    completed: bool = Field(strict=True)


class ValidatedStream(BaseModel):
    header: HeaderRecord
    pages: list[PageRecord]
    trailer: TrailerRecord
    page_hashes: list[str]
    document_hash: str
    quality_flags: list[list[str]]


def validate_header(
    record: dict[str, object],
    request_id: str | None = None,
    file_hash: str | None = None,
) -> HeaderRecord:
    """Validate toolchain and request identity immediately after the first line."""
    try:
        header = HeaderRecord.model_validate(record)
    except ValueError as exc:
        raise ContractValidationError("Invalid extractor header") from exc
    if any(getattr(header, key) != value for key, value in identity().items()):
        raise ContractValidationError("Extractor toolchain identity mismatch")
    if request_id is not None and header.request_id != request_id:
        raise ContractValidationError("Extractor request identity mismatch")
    if file_hash is not None and header.file_sha256 != file_hash:
        raise ContractValidationError("Extractor file identity mismatch")
    return header


def page_hash(page: PageRecord) -> str:
    """Hash every source field including styles, excluding the self hash."""
    return record_hash(page.model_dump(exclude={"page_content_hash"}))


def validate_page(record: dict[str, object], expected_page: int) -> PageRecord:
    """Validate a bounded page and independently recompute its hash."""
    try:
        page = PageRecord.model_validate(record)
        if (
            page.page_number != expected_page
            or page_hash(page) != page.page_content_hash
        ):
            raise ValueError("Page identity mismatch")
        return page
    except (ValueError, UnicodeError) as exc:
        raise ContractValidationError("Invalid extractor page") from exc


def validate_records(records: Sequence[dict[str, object]]) -> ValidatedStream:
    """Reject malformed, incomplete, non-contiguous or tampered extractor output."""
    from app.modules.document_anchor.quality import page_quality

    if len(records) < 3:
        raise ContractValidationError("Incomplete extractor stream")
    header = validate_header(records[0])
    pages = [
        validate_page(record, index) for index, record in enumerate(records[1:-1], 1)
    ]
    try:
        trailer = TrailerRecord.model_validate(records[-1])
    except ValueError as exc:
        raise ContractValidationError("Invalid extractor trailer") from exc
    hashes = [page.page_content_hash for page in pages]
    content_hash = document_content_hash(hashes)
    if (
        len(pages) != header.page_count
        or trailer.request_id != header.request_id
        or not trailer.completed
        or trailer.pages_emitted != len(pages)
        or trailer.items_emitted != sum(len(page.items) for page in pages)
        or trailer.document_content_hash != content_hash
    ):
        raise ContractValidationError("Incomplete or tampered extractor trailer")
    return ValidatedStream(
        header=header,
        pages=pages,
        trailer=trailer,
        page_hashes=hashes,
        document_hash=content_hash,
        quality_flags=[page_quality(page)[1] for page in pages],
    )
