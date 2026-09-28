"""精确绑定的人工确认服务。"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_service import ArtifactService
from app.agents.confirmation_model import RoleDecisionRecord, UserConfirmationRecord
from app.agents.confirmation_policy import (
    CONFIRMATION_POLICY_VERSION,
    required_role_for,
)
from app.agents.contracts import ArtifactRef
from app.agents.enums import ConfirmationStatus
from app.agents.errors import RevisionConflictError
from app.agents.hash_schema import content_hash
from app.agents.outbox_service import OutboxService
from app.agents.permission_service import PermissionService
from app.agents.revision_resolver import RevisionResolver


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class ConfirmationService:
    def __init__(
        self,
        permissions: PermissionService | None = None,
        artifacts: ArtifactService | None = None,
        outbox: OutboxService | None = None,
        revisions: RevisionResolver | None = None,
    ) -> None:
        self._permissions = permissions or PermissionService()
        self._artifacts = artifacts or ArtifactService()
        self._outbox = outbox or OutboxService()
        self._revisions = revisions or RevisionResolver()

    async def request(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        actor_scope: str,
        action: str,
        target_refs: tuple[ArtifactRef, ...],
        expected_revisions: dict[str, int],
        expires_in: timedelta = timedelta(hours=24),
    ) -> UserConfirmationRecord:
        await self._permissions.require_membership(
            session, research_context_id, actor_scope
        )
        required_role_for(action, CONFIRMATION_POLICY_VERSION)
        await self._revisions.assert_current(session, expected_revisions)
        for ref in target_refs:
            await self._artifacts.resolve(
                session, ref, research_context_id=research_context_id
            )
        canonical_targets = sorted(
            (ref.model_dump(mode="json") for ref in target_refs),
            key=lambda item: (
                str(item["artifact_type"]),
                str(item["artifact_id"]),
                str(item["version_key"]),
            ),
        )
        binding_hash = content_hash(
            {
                "action": action,
                "policy_version": CONFIRMATION_POLICY_VERSION,
                "research_context_id": research_context_id,
                "target_refs": canonical_targets,
                "expected_revisions": dict(sorted(expected_revisions.items())),
            }
        )
        existing = await session.scalar(
            select(UserConfirmationRecord).where(
                UserConfirmationRecord.research_context_id == research_context_id,
                UserConfirmationRecord.actor_scope == actor_scope,
                UserConfirmationRecord.action == action,
                UserConfirmationRecord.binding_hash == binding_hash,
                UserConfirmationRecord.status == ConfirmationStatus.PENDING,
            )
        )
        if existing is not None:
            return existing
        now = datetime.now(UTC)
        record = UserConfirmationRecord(
            confirmation_id=str(uuid4()),
            research_context_id=research_context_id,
            actor_scope=actor_scope,
            action=action,
            policy_version=CONFIRMATION_POLICY_VERSION,
            target_refs_json=canonical_targets,
            binding_hash=binding_hash,
            expected_revisions_json=expected_revisions,
            issued_at=now,
            expires_at=now + expires_in,
            consumed_at=None,
            status=ConfirmationStatus.PENDING,
            revision=1,
        )
        session.add(record)
        self._outbox.add(
            session,
            aggregate_type="confirmation",
            aggregate_id=record.confirmation_id,
            event_type="confirmation.requested",
            payload={
                "confirmation_id": record.confirmation_id,
                "research_context_id": research_context_id,
                "action": action,
                "binding_hash": binding_hash,
                "revision": 1,
            },
        )
        await session.flush()
        return record

    async def consume(
        self,
        session: AsyncSession,
        *,
        confirmation_id: str,
        expected_revision: int,
        actor_scope: str,
        decision: str,
        reason: str | None = None,
    ) -> RoleDecisionRecord:
        confirmation = await session.get(UserConfirmationRecord, confirmation_id)
        if confirmation is None:
            raise KeyError(confirmation_id)
        await self._permissions.require_membership(
            session, confirmation.research_context_id, actor_scope
        )
        authorized_role = required_role_for(
            confirmation.action, confirmation.policy_version
        )
        if authorized_role != "user_owner":
            await self._permissions.require_qualification(
                session, actor_scope, authorized_role
            )
        if confirmation.actor_scope != actor_scope:
            raise RevisionConflictError("confirmation belongs to another actor")
        if confirmation.status != ConfirmationStatus.PENDING:
            existing = await session.scalar(
                select(RoleDecisionRecord).where(
                    RoleDecisionRecord.confirmation_id == confirmation_id
                )
            )
            if existing is not None and existing.decision == decision:
                return existing
            raise RevisionConflictError("confirmation is no longer pending")
        for raw_ref in confirmation.target_refs_json:
            await self._artifacts.resolve(
                session,
                ArtifactRef.model_validate(raw_ref),
                research_context_id=confirmation.research_context_id,
            )
        await self._revisions.assert_current(
            session, confirmation.expected_revisions_json
        )
        now = datetime.now(UTC)
        if _as_utc(confirmation.expires_at) <= now:
            raise RevisionConflictError("confirmation expired")
        if decision not in {"approve", "reject"}:
            raise ValueError("decision must be approve or reject")
        result = await session.execute(
            update(UserConfirmationRecord)
            .where(
                UserConfirmationRecord.confirmation_id == confirmation_id,
                UserConfirmationRecord.revision == expected_revision,
                UserConfirmationRecord.status == ConfirmationStatus.PENDING,
            )
            .values(
                status=ConfirmationStatus.CONSUMED,
                consumed_at=now,
                revision=UserConfirmationRecord.revision + 1,
            )
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        decision_payload = {
            "confirmation_id": confirmation_id,
            "actor_scope": actor_scope,
            "authorized_role": authorized_role,
            "decision": decision,
            "target_binding_hash": confirmation.binding_hash,
            "target_refs": confirmation.target_refs_json,
            "reason": reason,
        }
        record = RoleDecisionRecord(
            decision_id=str(uuid4()),
            version_id=str(uuid4()),
            content_hash=content_hash(decision_payload),
            research_context_id=confirmation.research_context_id,
            confirmation_id=confirmation_id,
            actor_scope=actor_scope,
            authorized_role=authorized_role,
            decision=decision,
            target_refs_json=confirmation.target_refs_json,
            target_binding_hash=confirmation.binding_hash,
            reason=reason,
            decided_at=now,
        )
        session.add(record)
        self._outbox.add(
            session,
            aggregate_type="confirmation",
            aggregate_id=confirmation_id,
            event_type="confirmation.recorded",
            payload={
                "confirmation_id": confirmation_id,
                "decision_id": record.decision_id,
                "decision": decision,
                "authorized_role": authorized_role,
                "binding_hash": confirmation.binding_hash,
            },
        )
        await session.flush()
        return record
