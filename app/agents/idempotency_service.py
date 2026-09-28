"""公共幂等查询和写入。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.errors import IdempotencyKeyReusedError
from app.agents.idempotency_model import AgentIdempotencyRecord


class IdempotencyService:
    async def find(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        actor_scope: str,
        action: str,
        key: str,
        request_hash: str,
    ) -> AgentIdempotencyRecord | None:
        record = await session.scalar(
            select(AgentIdempotencyRecord).where(
                AgentIdempotencyRecord.research_context_id == research_context_id,
                AgentIdempotencyRecord.actor_scope == actor_scope,
                AgentIdempotencyRecord.action == action,
                AgentIdempotencyRecord.idempotency_key == key,
            )
        )
        if record is not None and record.request_hash != request_hash:
            raise IdempotencyKeyReusedError()
        return record

    def add(
        self,
        session: AsyncSession,
        *,
        research_context_id: str,
        actor_scope: str,
        action: str,
        key: str,
        request_hash: str,
        resource_type: str,
        resource_id: str,
        resource_version: str | None,
    ) -> AgentIdempotencyRecord:
        record = AgentIdempotencyRecord(
            idempotency_id=str(uuid4()),
            research_context_id=research_context_id,
            actor_scope=actor_scope,
            action=action,
            idempotency_key=key,
            request_hash=request_hash,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_version=resource_version,
            created_at=datetime.now(UTC),
        )
        session.add(record)
        return record
