"""Machine-readable coverage and publish-readiness contracts."""

from typing import Literal

from pydantic import BaseModel, Field

CoverageStatus = Literal["supported", "missing_citation", "needs_verification", "conflict", "unverifiable"]


class ParagraphCoverage(BaseModel):
    segment_id: str
    status: CoverageStatus
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PublishReadinessRead(BaseModel):
    passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    paragraphs: list[ParagraphCoverage] = Field(default_factory=list)
