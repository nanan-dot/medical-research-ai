"""M0 公共运行时 API 契约。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.agents.authorization_contract import ContentGranularity, DataCategory
from app.agents.contracts import ArtifactRef


class TaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    research_context_id: int | str
    requested_agent: Literal["A1", "A2", "A3", "A4", "A5"]
    intent: str = Field(min_length=1, max_length=128)
    input_artifact_refs: list[ArtifactRef] = Field(default_factory=list)
    authorization_refs: list[ArtifactRef] = Field(default_factory=list)


class TaskRead(BaseModel):
    task_request_id: str
    research_context_id: str
    requested_agent: str
    intent: str
    request_hash: str


class RuntimeRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    research_context_id: int | str
    task_request_id: str
    agent_type: Literal["A1", "A2", "A3", "A4", "A5"]
    run_mode: Literal["standalone_confirmation", "composite_workflow"]


class RuntimeRunRead(BaseModel):
    run_id: str
    research_context_id: str | None
    task_request_id: str | None
    agent_type: str | None
    run_mode: str | None
    status: str
    phase: str | None
    reason_code: str | None
    revision: int


class RuntimeCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)


class RuntimeRecoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)


class ConfirmationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    research_context_id: int | str
    action: str = Field(min_length=1, max_length=64)
    target_refs: list[ArtifactRef] = Field(min_length=1)
    expected_revisions: dict[str, int]
    expires_in_seconds: int = Field(default=86400, ge=60, le=604800)


class ConfirmationRead(BaseModel):
    confirmation_id: str
    binding_hash: str
    status: str
    revision: int
    expires_at: datetime


class ConfirmationDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    decision: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=1000)


class DecisionRead(BaseModel):
    decision_id: str
    version_id: str
    content_hash: str
    decision: str
    authorized_role: str


class AuthorizationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    research_context_id: int | str
    provider: str
    model: str
    purpose: str
    content_granularity: ContentGranularity
    data_categories: list[DataCategory] = Field(min_length=1)
    payload_refs: list[ArtifactRef]
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    payload_shape: Literal["single_item", "multi_item_bundle"]
    content_transform: Literal["raw", "deidentified", "aggregated"]
    allow_cloud_transfer: bool
    expires_in_seconds: int = Field(default=1800, ge=60, le=86400)


class AuthorizationRead(BaseModel):
    authorization_id: str
    status: str
    revision: int
    expires_at: datetime


class AuthorizationRevokeRequest(BaseModel):
    expected_revision: int = Field(ge=1)


class ArtifactResolveRequest(BaseModel):
    research_context_id: int | str
    artifact_ref: ArtifactRef


class ArtifactResolveRead(BaseModel):
    artifact_ref: ArtifactRef
    typed_ref: dict[str, object]
