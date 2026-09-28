"""不可变 TaskRequest 创建服务。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.artifact_service import ArtifactService
from app.agents.contracts import ArtifactRef, TaskRequest
from app.agents.hash_schema import content_hash
from app.agents.permission_service import PermissionService
from app.agents.runtime_model import AgentTaskRequestRecord


class TaskRequestService:
    def __init__(
        self,
        permissions: PermissionService | None = None,
        artifacts: ArtifactService | None = None,
    ) -> None:
        self._permissions = permissions or PermissionService()
        self._artifacts = artifacts or ArtifactService()

    async def create(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        actor_scope: str,
        requested_agent: str,
        intent: str,
        input_refs: tuple[ArtifactRef, ...] = (),
        authorization_refs: tuple[ArtifactRef, ...] = (),
    ) -> TaskRequest:
        await self._permissions.require_membership(
            session, research_context_id, actor_scope
        )
        for ref in (*input_refs, *authorization_refs):
            await self._artifacts.resolve(
                session, ref, research_context_id=research_context_id
            )
        ordered_inputs = tuple(
            sorted(
                input_refs,
                key=lambda ref: (ref.artifact_type, ref.artifact_id, ref.version_key),
            )
        )
        ordered_auth = tuple(
            sorted(
                authorization_refs,
                key=lambda ref: (ref.artifact_type, ref.artifact_id, ref.version_key),
            )
        )
        payload = {
            "research_context_id": research_context_id,
            "requested_agent": requested_agent,
            "intent": intent,
            "input_artifact_refs": [
                ref.model_dump(mode="json") for ref in ordered_inputs
            ],
            "authorization_refs": [ref.model_dump(mode="json") for ref in ordered_auth],
        }
        digest = content_hash(payload)
        task_request_id = str(uuid4())
        record = AgentTaskRequestRecord(
            task_request_id=task_request_id,
            research_context_id=research_context_id,
            requested_agent=requested_agent,
            intent=intent,
            input_artifact_refs_json=payload["input_artifact_refs"],
            authorization_refs_json=payload["authorization_refs"],
            request_hash=digest,
            created_by=actor_scope,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        await session.flush()
        return TaskRequest(
            task_request_id=task_request_id,
            research_context_id=research_context_id,
            requested_agent=requested_agent,
            intent=intent,
            input_artifact_refs=ordered_inputs,
            authorization_refs=ordered_auth,
            request_hash=digest,
        )
