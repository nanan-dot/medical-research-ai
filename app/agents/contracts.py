"""M0 跨模块传递的不可变契约。"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_id: str
    artifact_type: str
    research_context_id: str
    artifact_key: str
    version_key: str
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_version: str
    validity_status: Literal[
        "valid", "needs_revalidation", "stale", "superseded", "invalid"
    ]


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_request_id: str
    research_context_id: str
    requested_agent: str
    intent: str
    input_artifact_refs: tuple[ArtifactRef, ...] = ()
    authorization_refs: tuple[ArtifactRef, ...] = ()
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class AgentEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detail_kind: str
    detail: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: tuple[ArtifactRef, ...] = ()


class DependencyRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    upstream_artifact_id: str
    upstream_version_key: str
    upstream_content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependency_kind: str
