"""Artifact 失效写入和下游读取门禁。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_model import (
    AgentArtifactRecord,
    ArtifactDependencyRecord,
    InvalidationRecord,
)
from app.agents.artifact_registry import policy_for
from app.agents.confirmation_model import UserConfirmationRecord
from app.agents.enums import ArtifactValidityStatus, ConfirmationStatus
from app.agents.errors import RevisionConflictError
from app.agents.outbox_service import OutboxService


class InvalidationService:
    def __init__(self, outbox: OutboxService | None = None) -> None:
        self._outbox = outbox or OutboxService()

    async def invalidate(
        self,
        session: AsyncSession,
        *,
        artifact_id: str,
        reason_code: str,
        upstream_artifact_id: str | None = None,
    ) -> InvalidationRecord:
        root = await session.get(AgentArtifactRecord, artifact_id)
        if root is None:
            raise KeyError(artifact_id)
        if root.validity_status != ArtifactValidityStatus.VALID:
            raise RevisionConflictError("artifact validity already changed")

        first_record: InvalidationRecord | None = None
        pending: list[
            tuple[AgentArtifactRecord, ArtifactValidityStatus, str | None]
        ] = [(
            root,
            policy_for(root.artifact_type, root.registry_version).downstream_status,
            upstream_artifact_id,
        )]
        visited: set[str] = set()
        affected_ids: set[str] = set()
        while pending:
            artifact, target_status, direct_upstream_id = pending.pop(0)
            if artifact.artifact_id in visited:
                continue
            visited.add(artifact.artifact_id)
            if artifact.validity_status != ArtifactValidityStatus.VALID:
                continue
            record = await self._invalidate_one(
                session,
                artifact=artifact,
                next_status=target_status,
                reason_code=reason_code,
                upstream_artifact_id=direct_upstream_id,
            )
            first_record = first_record or record
            affected_ids.add(artifact.artifact_id)
            dependency_rows = await session.scalars(
                select(ArtifactDependencyRecord).where(
                    ArtifactDependencyRecord.upstream_artifact_id
                    == artifact.artifact_id
                )
            )
            for dependency in dependency_rows:
                downstream = await session.get(
                    AgentArtifactRecord, dependency.downstream_artifact_id
                )
                if downstream is not None:
                    pending.append(
                        (
                            downstream,
                            policy_for(
                                downstream.artifact_type, downstream.registry_version
                            ).downstream_status,
                            artifact.artifact_id,
                        )
                    )
        await self._supersede_pending_confirmations(session, affected_ids)
        await session.flush()
        assert first_record is not None
        return first_record

    async def supersede(
        self,
        session: AsyncSession,
        *,
        artifact_id: str,
        replacement_artifact_id: str,
        reason_code: str = "explicit_replacement",
    ) -> InvalidationRecord:
        """Replace one immutable version; ordinary invalidation cannot choose this state."""
        if reason_code != "explicit_replacement":
            raise ValueError("supersede requires explicit_replacement reason")
        root = await session.get(AgentArtifactRecord, artifact_id)
        replacement = await session.get(AgentArtifactRecord, replacement_artifact_id)
        if root is None or replacement is None:
            raise KeyError(artifact_id if root is None else replacement_artifact_id)
        if (
            root.artifact_id == replacement.artifact_id
            or root.research_context_id != replacement.research_context_id
            or root.artifact_type != replacement.artifact_type
            or root.artifact_key != replacement.artifact_key
            or root.version_key == replacement.version_key
            or replacement.validity_status != ArtifactValidityStatus.VALID
        ):
            raise ValueError("invalid replacement artifact")
        if root.validity_status != ArtifactValidityStatus.VALID:
            raise RevisionConflictError("artifact validity already changed")
        record = await self._invalidate_one(
            session,
            artifact=root,
            next_status=ArtifactValidityStatus.SUPERSEDED,
            reason_code=reason_code,
            upstream_artifact_id=replacement.artifact_id,
        )
        affected_ids = await self._propagate_from(session, root, reason_code)
        await self._supersede_pending_confirmations(session, affected_ids)
        await session.flush()
        return record

    async def _propagate_from(
        self, session: AsyncSession, root: AgentArtifactRecord, reason_code: str
    ) -> set[str]:
        pending = [root]
        visited: set[str] = set()
        affected_ids: set[str] = set()
        while pending:
            upstream = pending.pop(0)
            if upstream.artifact_id in visited:
                continue
            visited.add(upstream.artifact_id)
            affected_ids.add(upstream.artifact_id)
            rows = await session.scalars(
                select(ArtifactDependencyRecord).where(
                    ArtifactDependencyRecord.upstream_artifact_id
                    == upstream.artifact_id
                )
            )
            for dependency in rows:
                downstream = await session.get(
                    AgentArtifactRecord, dependency.downstream_artifact_id
                )
                if (
                    downstream is None
                    or downstream.artifact_id in visited
                ):
                    continue
                if downstream.validity_status == ArtifactValidityStatus.VALID:
                    await self._invalidate_one(
                        session,
                        artifact=downstream,
                        next_status=policy_for(
                            downstream.artifact_type, downstream.registry_version
                        ).downstream_status,
                        reason_code=reason_code,
                        upstream_artifact_id=upstream.artifact_id,
                    )
                pending.append(downstream)
        return affected_ids

    async def _invalidate_one(
        self,
        session: AsyncSession,
        *,
        artifact: AgentArtifactRecord,
        next_status: ArtifactValidityStatus,
        reason_code: str,
        upstream_artifact_id: str | None,
    ) -> InvalidationRecord:
        result = await session.execute(
            update(AgentArtifactRecord)
            .where(
                AgentArtifactRecord.artifact_id == artifact.artifact_id,
                AgentArtifactRecord.validity_status == ArtifactValidityStatus.VALID,
            )
            .values(validity_status=next_status)
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        outbox = self._outbox.add(
            session,
            aggregate_type="artifact",
            aggregate_id=artifact.artifact_id,
            event_type="artifact.invalidated",
            payload={
                "artifact_id": artifact.artifact_id,
                "upstream_artifact_id": upstream_artifact_id,
                "next_status": next_status,
                "reason_code": reason_code,
            },
        )
        record = InvalidationRecord(
            invalidation_id=str(uuid4()),
            target_artifact_id=artifact.artifact_id,
            upstream_artifact_id=upstream_artifact_id,
            reason_code=reason_code,
            old_content_hash=artifact.content_hash,
            status=next_status,
            event_id=outbox.event_id,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        return record

    async def _supersede_pending_confirmations(
        self, session: AsyncSession, affected_ids: set[str]
    ) -> None:
        if not affected_ids:
            return
        confirmations = await session.scalars(
            select(UserConfirmationRecord).where(
                UserConfirmationRecord.status == ConfirmationStatus.PENDING
            )
        )
        for confirmation in confirmations:
            target_ids = {
                str(ref.get("artifact_id"))
                for ref in confirmation.target_refs_json
                if isinstance(ref, dict)
            }
            if target_ids.isdisjoint(affected_ids):
                continue
            confirmation.status = ConfirmationStatus.SUPERSEDED
            confirmation.revision += 1
            self._outbox.add(
                session,
                aggregate_type="confirmation",
                aggregate_id=confirmation.confirmation_id,
                event_type="confirmation.superseded",
                payload={
                    "confirmation_id": confirmation.confirmation_id,
                    "binding_hash": confirmation.binding_hash,
                    "revision": confirmation.revision,
                    "reason_code": "target_invalidated",
                },
            )
