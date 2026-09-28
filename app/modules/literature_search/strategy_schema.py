"""Typed HTTP contracts for the strategy workspace."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TermSource = Literal["research_question", "smart_expansion", "user_added"]
MeshVerificationStatus = Literal["verified", "not_found", "unavailable", "stale"]


class StrategyCreate(BaseModel):
    research_question: str = Field(min_length=1, max_length=1000)
    intent_mode: str = Field(default="unstructured", max_length=40)
    intent: dict[str, object] = Field(default_factory=dict)
    limits: dict[str, object] = Field(default_factory=dict)
    query_text: str = Field(default="", max_length=5000)
    terms: list["StrategyTermCreate"] = Field(default_factory=list, max_length=100)
    mesh_terms: list["StrategyMeshCreate"] = Field(default_factory=list, max_length=100)


class StrategyPatch(BaseModel):
    revision: int = Field(ge=1)
    research_question: str | None = Field(default=None, min_length=1, max_length=1000)
    intent_mode: str | None = Field(default=None, max_length=40)
    intent: dict[str, object] | None = None
    limits: dict[str, object] | None = None
    query_text: str | None = Field(default=None, max_length=5000)
    query_source: Literal["generated", "user_edited"] | None = None


class StrategyTermCreate(BaseModel):
    text: str = Field(min_length=1, max_length=300)
    concept_group: str = Field(min_length=1, max_length=80)
    source: TermSource
    field_tag: str | None = Field(default=None, max_length=80)
    relation_type: str | None = Field(default=None, max_length=80)
    is_locked: bool = False


class StrategyMeshCreate(BaseModel):
    descriptor: str = Field(min_length=1, max_length=300)
    mesh_id: str | None = Field(default=None, max_length=80)
    concept_group: str = Field(min_length=1, max_length=80)
    source: Literal["nlm_mesh"] = "nlm_mesh"
    verification_status: MeshVerificationStatus = "stale"
    is_locked: bool = False


class StrategyTermPatch(BaseModel):
    is_locked: bool | None = None
    text: str | None = Field(default=None, min_length=1, max_length=300)


class StrategyTermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    concept_group: str
    text: str
    source: str
    field_tag: str | None
    relation_type: str | None
    is_locked: bool
    warning: dict[str, str] | None = None


class StrategyMeshRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    descriptor: str
    mesh_id: str | None
    concept_group: str
    source: str
    verification_status: str
    is_locked: bool
    verification_checked_at: datetime | None


class StrategyMeshPatch(BaseModel):
    is_locked: bool


class StrategyRead(BaseModel):
    id: int
    research_question: str
    intent_mode: str
    intent: dict[str, object]
    limits: dict[str, object]
    query_text: str
    query_source: str
    fingerprint: str
    revision: int
    generation_state: str
    validation_state: str
    count_state: str
    count: dict[str, object]
    last_saved_at: datetime
    terms: list[StrategyTermRead]
    mesh_terms: list[StrategyMeshRead]


class StrategyRemapRead(BaseModel):
    revision: int
    fingerprint: str
    terms: list[StrategyTermRead]


class StrategyVersionRead(BaseModel):
    id: int
    strategy_id: int
    version: int
    fingerprint: str
    note: str | None
    created_at: datetime


class StrategyValidationRead(BaseModel):
    is_syntax_valid: bool
    is_mesh_valid: bool
    are_field_tags_valid: bool
    warnings: list[dict[str, str]]
    blocking_errors: list[dict[str, str]]
    validated_fingerprint: str
    validated_at: datetime


class StrategyCountRead(BaseModel):
    count: int
    fingerprint: str
    retrieved_at: datetime
    source: Literal["pubmed"]


class StrategyCompareRead(BaseModel):
    from_version: int
    to_version: int
    changes: dict[str, object]
