"""Bounded public contracts for A3 candidates and human decisions."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target_anchor_revision_id: int = Field(gt=0, strict=True)


class CandidateRead(BaseModel):
    id: int
    source_anchor_id: int
    target_anchor_revision_id: int
    candidate_anchor_id: int | None
    method: str
    algorithm_version: str
    score_breakdown: dict[str, float]
    protected_token_status: str
    status: str
    decision_source: str | None
    created_at: datetime


class DecisionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_type: Literal["document_annotation", "document_reading_note"]
    asset_id: int = Field(gt=0, strict=True)
    candidate_id: int = Field(gt=0, strict=True)
    decision: Literal["confirm", "reject", "supersede"]
    expected_resolution_version: int = Field(gt=0, strict=True)
    decision_note: str | None = Field(default=None, max_length=1000)


class AssetResolutionRead(BaseModel):
    asset_type: str
    asset_id: int
    original_anchor_id: int
    resolved_anchor_id: int | None
    resolution_status: str
    resolution_version: int


class BackfillRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    asset_type: Literal["document_annotation", "citation"]
    source_schema_version: str = Field(min_length=1, max_length=64)
    target_anchor_revision_id: int = Field(gt=0, strict=True)
    mode: Literal["dry_run", "apply"]


class BackfillRunRead(BaseModel):
    id: int
    task_id: int | None
    asset_type: str
    target_anchor_revision_id: int | None
    mode: str
    cursor: str | None
    total: int
    scanned: int
    exact: int
    candidate: int
    unresolved: int
    failed: int
    algorithm_version: str
    status: str
    report_json: str


class ResolutionIssueRead(BaseModel):
    asset_type: str
    asset_id: int
    original_anchor_id: int
    resolved_anchor_id: int | None
    resolution_status: str
    resolution_version: int
    candidate_count: int


__all__ = [
    "AssetResolutionRead",
    "BackfillRunCreate",
    "BackfillRunRead",
    "CandidateRead",
    "CandidateRequest",
    "DecisionCreate",
    "ResolutionIssueRead",
]
