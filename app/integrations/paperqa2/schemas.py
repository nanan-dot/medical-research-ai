"""Stable application-facing structures for the PaperQA2 adapter."""

from pathlib import Path

from pydantic import BaseModel, Field


class PaperQA2Config(BaseModel):
    version: str = Field(min_length=1)
    ollama_base_url: str = Field(min_length=1)
    llm_model: str = Field(min_length=1)
    embedding_model: str = Field(min_length=1)
    timeout_seconds: float = Field(default=300.0, gt=0)


class PaperDocument(BaseModel):
    path: Path
    citation: str | None = None
    title: str | None = None


class PaperQAIndex(BaseModel):
    index_id: str = Field(min_length=1)
    document_count: int = Field(ge=1)
    reused: bool


class PaperSource(BaseModel):
    source_id: str | None = None
    title: str | None = None
    citation: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)
    excerpt: str | None = None
    score: float | None = None


class PaperQAAnswer(BaseModel):
    answer: str = Field(min_length=1)
    index_id: str = Field(min_length=1)
    sources: list[PaperSource] = Field(default_factory=list)
