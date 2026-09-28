"""模型内容外发授权的创建、撤销和双重校验。"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_service import ArtifactService
from app.agents.authorization_contract import normalize_authorization_scope
from app.agents.authorization_model import ModelTransferAuthorizationRecord
from app.agents.contracts import ArtifactRef
from app.agents.enums import AuthorizationStatus
from app.agents.errors import AuthorizationRejectedError, RevisionConflictError
from app.agents.permission_service import PermissionService


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


class AuthorizationService:
    def __init__(
        self,
        permissions: PermissionService | None = None,
        artifacts: ArtifactService | None = None,
    ) -> None:
        self._permissions = permissions or PermissionService()
        self._artifacts = artifacts or ArtifactService()

    async def issue(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        actor_scope: str,
        provider: str,
        model: str,
        purpose: str,
        content_granularity: str,
        data_categories: tuple[str, ...],
        payload_refs: list[ArtifactRef],
        payload_hash: str,
        payload_shape: str,
        content_transform: str,
        allow_cloud_transfer: bool,
        expires_in: timedelta = timedelta(minutes=30),
    ) -> ModelTransferAuthorizationRecord:
        content_granularity, normalized_categories = normalize_authorization_scope(
            content_granularity, data_categories
        )
        await self._permissions.require_membership(
            session, research_context_id, actor_scope
        )
        if content_transform not in {"raw", "deidentified", "aggregated"}:
            raise ValueError("invalid content transform")
        if payload_shape not in {"single_item", "multi_item_bundle"}:
            raise ValueError("invalid payload shape")
        for ref in payload_refs:
            await self._artifacts.resolve(
                session, ref, research_context_id=research_context_id
            )
        now = datetime.now(UTC)
        record = ModelTransferAuthorizationRecord(
            authorization_id=str(uuid4()),
            research_context_id=research_context_id,
            actor_scope=actor_scope,
            provider_scope=provider,
            model_scope=model,
            purpose=purpose,
            content_granularity=content_granularity,
            data_categories_json=list(normalized_categories),
            payload_refs_json=[ref.model_dump(mode="json") for ref in payload_refs],
            payload_hash=payload_hash,
            payload_shape=payload_shape,
            content_transform=content_transform,
            allow_cloud_transfer=allow_cloud_transfer,
            issued_at=now,
            expires_at=now + expires_in,
            revoked_at=None,
            status=AuthorizationStatus.ACTIVE,
            revision=1,
        )
        session.add(record)
        await session.flush()
        return record

    async def assert_allowed(
        self,
        session: AsyncSession,
        *,
        authorization_id: str,
        research_context_id: str,
        actor_scope: str,
        provider: str,
        model: str,
        purpose: str,
        content_granularity: str,
        data_categories: tuple[str, ...],
        payload_refs: tuple[ArtifactRef, ...],
        payload_hash: str,
        payload_shape: str,
        content_transform: str,
        is_cloud: bool,
    ) -> ModelTransferAuthorizationRecord:
        try:
            content_granularity, normalized_categories = normalize_authorization_scope(
                content_granularity, data_categories
            )
        except ValueError as exc:
            raise AuthorizationRejectedError("authorization vocabulary rejected") from exc
        authorization = await session.get(
            ModelTransferAuthorizationRecord, authorization_id
        )
        now = datetime.now(UTC)
        actual_refs = sorted(
            (ref.model_dump(mode="json") for ref in payload_refs),
            key=lambda item: (
                str(item["artifact_type"]),
                str(item["artifact_id"]),
                str(item["version_key"]),
            ),
        )
        stored_refs = sorted(
            authorization.payload_refs_json if authorization is not None else [],
            key=lambda item: (
                str(item["artifact_type"]),
                str(item["artifact_id"]),
                str(item["version_key"]),
            ),
        )
        if (
            authorization is None
            or authorization.research_context_id != research_context_id
            or authorization.actor_scope != actor_scope
            or authorization.provider_scope != provider
            or authorization.model_scope != model
            or authorization.purpose != purpose
            or authorization.content_granularity != content_granularity
            or authorization.data_categories_json != list(normalized_categories)
            or stored_refs != actual_refs
            or authorization.payload_hash != payload_hash
            or authorization.payload_shape != payload_shape
            or authorization.content_transform != content_transform
            or authorization.status != AuthorizationStatus.ACTIVE
            or authorization.revoked_at is not None
            or _as_utc(authorization.expires_at) <= now
            or (is_cloud and not authorization.allow_cloud_transfer)
        ):
            raise AuthorizationRejectedError()
        if payload_shape == "single_item" and len(payload_refs) > 1:
            raise AuthorizationRejectedError(
                "single_item authorization has multiple refs"
            )
        if payload_shape == "multi_item_bundle" and len(payload_refs) < 2:
            raise AuthorizationRejectedError(
                "bundle authorization requires multiple refs"
            )
        for ref in payload_refs:
            await self._artifacts.resolve(
                session, ref, research_context_id=research_context_id
            )
        return authorization

    async def revoke(
        self,
        session: AsyncSession,
        *,
        authorization_id: str,
        expected_revision: int,
        actor_scope: str,
    ) -> ModelTransferAuthorizationRecord:
        authorization = await session.get(
            ModelTransferAuthorizationRecord, authorization_id
        )
        if authorization is None:
            raise KeyError(authorization_id)
        await self._permissions.require_membership(
            session, authorization.research_context_id, actor_scope
        )
        if authorization.actor_scope != actor_scope:
            raise AuthorizationRejectedError("authorization belongs to another actor")
        if (
            authorization.status == AuthorizationStatus.REVOKED
            and authorization.revision == expected_revision + 1
        ):
            return authorization
        result = await session.execute(
            update(ModelTransferAuthorizationRecord)
            .where(
                ModelTransferAuthorizationRecord.authorization_id == authorization_id,
                ModelTransferAuthorizationRecord.revision == expected_revision,
                ModelTransferAuthorizationRecord.status == AuthorizationStatus.ACTIVE,
            )
            .values(
                status=AuthorizationStatus.REVOKED,
                revoked_at=datetime.now(UTC),
                revision=ModelTransferAuthorizationRecord.revision + 1,
            )
        )
        assert isinstance(result, CursorResult)

        if result.rowcount != 1:
            raise RevisionConflictError()
        await session.flush()
        await session.refresh(authorization)
        return authorization
