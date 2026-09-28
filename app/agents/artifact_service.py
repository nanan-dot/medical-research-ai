"""不可变 Artifact 注册、解析和依赖门禁。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_model import AgentArtifactRecord, ArtifactDependencyRecord
from app.agents.artifact_registry import ARTIFACT_REGISTRY_VERSION, validate_typed_ref
from app.agents.contracts import ArtifactRef, DependencyRef
from app.agents.enums import ArtifactValidityStatus
from app.agents.errors import (
    ArtifactHashMismatchError,
    DependencyInvalidError,
    PermissionDeniedError,
    RevisionConflictError,
)
from app.agents.outbox_service import OutboxService


class ArtifactService:
    def __init__(self, outbox: OutboxService | None = None) -> None:
        self._outbox = outbox or OutboxService()

    async def register(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        artifact_type: str,
        artifact_key: str,
        version_key: str,
        schema_version: str,
        payload: dict[str, object],
        created_by: str,
        dependencies: tuple[DependencyRef, ...] = (),
    ) -> ArtifactRef:
        digest = validate_typed_ref(
            artifact_type=artifact_type,
            artifact_key=artifact_key,
            version_key=version_key,
            schema_version=schema_version,
            payload=payload,
            registry_version=ARTIFACT_REGISTRY_VERSION,
        )
        existing = await session.scalar(
            select(AgentArtifactRecord).where(
                AgentArtifactRecord.research_context_id == research_context_id,
                AgentArtifactRecord.artifact_type == artifact_type,
                AgentArtifactRecord.artifact_key == artifact_key,
                AgentArtifactRecord.version_key == version_key,
            )
        )
        if existing is not None:
            if existing.content_hash != digest:
                raise RevisionConflictError(
                    "artifact version already has different content"
                )
            stored_dependencies = await session.scalars(
                select(ArtifactDependencyRecord).where(
                    ArtifactDependencyRecord.downstream_artifact_id
                    == existing.artifact_id
                )
            )
            stored_identity = {
                (
                    item.upstream_artifact_id,
                    item.upstream_version_key,
                    item.upstream_content_hash,
                    item.dependency_kind,
                )
                for item in stored_dependencies
            }
            requested_identity = {
                (
                    item.upstream_artifact_id,
                    item.upstream_version_key,
                    item.upstream_content_hash,
                    item.dependency_kind,
                )
                for item in dependencies
            }
            if stored_identity != requested_identity:
                raise RevisionConflictError(
                    "artifact version already has different dependencies"
                )
            return self._ref(existing)

        upstream_records: list[AgentArtifactRecord] = []
        seen: set[tuple[str, str]] = set()
        for dependency in dependencies:
            identity = (
                dependency.upstream_artifact_id,
                dependency.upstream_version_key,
            )
            if identity in seen:
                raise DependencyInvalidError("duplicate dependency")
            seen.add(identity)
            upstream = await session.get(
                AgentArtifactRecord, dependency.upstream_artifact_id
            )
            if (
                upstream is None
                or upstream.research_context_id != research_context_id
                or upstream.version_key != dependency.upstream_version_key
                or upstream.content_hash != dependency.upstream_content_hash
                or upstream.validity_status != ArtifactValidityStatus.VALID
            ):
                raise DependencyInvalidError()
            upstream_records.append(upstream)

        record = AgentArtifactRecord(
            artifact_id=str(uuid4()),
            artifact_type=artifact_type,
            research_context_id=research_context_id,
            artifact_key=artifact_key,
            version_key=version_key,
            content_hash=digest,
            schema_version=schema_version,
            registry_version=ARTIFACT_REGISTRY_VERSION,
            validity_status=ArtifactValidityStatus.VALID,
            typed_ref_json=payload,
            created_by=created_by,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        await session.flush()
        for dependency, upstream in zip(dependencies, upstream_records, strict=True):
            session.add(
                ArtifactDependencyRecord(
                    dependency_id=str(uuid4()),
                    downstream_artifact_id=record.artifact_id,
                    upstream_artifact_id=upstream.artifact_id,
                    upstream_version_key=upstream.version_key,
                    upstream_content_hash=upstream.content_hash,
                    dependency_kind=dependency.dependency_kind,
                    created_at=datetime.now(UTC),
                )
            )
        self._outbox.add(
            session,
            aggregate_type="artifact",
            aggregate_id=record.artifact_id,
            event_type="artifact.created",
            payload={
                "artifact_id": record.artifact_id,
                "artifact_type": artifact_type,
                "research_context_id": research_context_id,
                "version_key": version_key,
                "content_hash": digest,
            },
        )
        return self._ref(record)

    async def resolve(
        self,
        session: AsyncSession,
        ref: ArtifactRef,
        *,
        research_context_id: str,
        require_valid: bool = True,
    ) -> AgentArtifactRecord:
        if ref.research_context_id != research_context_id:
            raise PermissionDeniedError()
        record = await session.get(AgentArtifactRecord, ref.artifact_id)
        if record is None or record.research_context_id != research_context_id:
            raise PermissionDeniedError()
        expected = self._ref(record)
        if (
            expected.artifact_type != ref.artifact_type
            or expected.artifact_key != ref.artifact_key
            or expected.version_key != ref.version_key
            or expected.content_hash != ref.content_hash
            or expected.schema_version != ref.schema_version
        ):
            raise ArtifactHashMismatchError()
        if (
            validate_typed_ref(
                artifact_type=record.artifact_type,
                artifact_key=record.artifact_key,
                version_key=record.version_key,
                schema_version=record.schema_version,
                payload=record.typed_ref_json,
                registry_version=record.registry_version,
            )
            != record.content_hash
        ):
            raise ArtifactHashMismatchError("stored artifact payload is corrupt")
        if require_valid and record.validity_status != ArtifactValidityStatus.VALID:
            raise DependencyInvalidError(record.validity_status)
        await self._validate_dependency_closure(session, record, research_context_id)
        return record

    async def _validate_dependency_closure(
        self,
        session: AsyncSession,
        root: AgentArtifactRecord,
        research_context_id: str,
    ) -> None:
        pending = [root.artifact_id]
        visited: set[str] = set()
        while pending:
            downstream_id = pending.pop()
            if downstream_id in visited:
                continue
            visited.add(downstream_id)
            dependencies = await session.scalars(
                select(ArtifactDependencyRecord).where(
                    ArtifactDependencyRecord.downstream_artifact_id == downstream_id
                )
            )
            for dependency in dependencies:
                upstream = await session.get(
                    AgentArtifactRecord, dependency.upstream_artifact_id
                )
                if (
                    upstream is None
                    or upstream.research_context_id != research_context_id
                    or upstream.version_key != dependency.upstream_version_key
                    or upstream.content_hash != dependency.upstream_content_hash
                    or upstream.validity_status != ArtifactValidityStatus.VALID
                    or validate_typed_ref(
                        artifact_type=upstream.artifact_type,
                        artifact_key=upstream.artifact_key,
                        version_key=upstream.version_key,
                        schema_version=upstream.schema_version,
                        payload=upstream.typed_ref_json,
                        registry_version=upstream.registry_version,
                    )
                    != upstream.content_hash
                ):
                    raise DependencyInvalidError()
                pending.append(upstream.artifact_id)

    @staticmethod
    def _ref(record: AgentArtifactRecord) -> ArtifactRef:
        return ArtifactRef.model_validate({
            "artifact_id": record.artifact_id,
            "artifact_type": record.artifact_type,
            "research_context_id": record.research_context_id,
            "artifact_key": record.artifact_key,
            "version_key": record.version_key,
            "content_hash": record.content_hash,
            "schema_version": record.schema_version,
            "validity_status": record.validity_status,
        })
