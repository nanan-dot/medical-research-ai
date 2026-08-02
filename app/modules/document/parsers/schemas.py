"""Stable parser result schemas independent of parser libraries."""

from pydantic import BaseModel, Field


class ParsedSection(BaseModel):
    heading: str
    level: int = Field(ge=1, le=6)
    text: str


class ParsedPage(BaseModel):
    page_number: int = Field(ge=1)
    text: str


class ParsedDocument(BaseModel):
    source_path: str
    title: str | None
    text: str
    pages: list[ParsedPage] = Field(default_factory=list)
    sections: list[ParsedSection] = Field(default_factory=list)
    yaml_metadata: dict[str, object] = Field(default_factory=dict)
    is_scanned: bool = False


class ParsedContentSummary(BaseModel):
    document_id: int
    title: str | None
    page_count: int
    page_numbers: list[int]
    section_headings: list[str]
    yaml_metadata: dict[str, object]
    is_scanned: bool
    character_count: int
