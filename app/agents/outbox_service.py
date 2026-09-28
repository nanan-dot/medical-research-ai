"""Outbox 写入和发布确认。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.enums import PUBLIC_EVENT_TYPES
from app.agents.hash_schema import canonical_json, content_hash
from app.agents.outbox_model import AgentOutboxRecord


class OutboxService:
    def add(
        self,
        session: AsyncSession,
        *,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: dict[str, object],
        event_id: str | None = None,
    ) -> AgentOutboxRecord:
        if event_type not in PUBLIC_EVENT_TYPES:
            raise ValueError("event type is not part of the frozen public contract")
        record = AgentOutboxRecord(
            event_id=event_id or str(uuid4()),
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload_json=canonical_json(payload).decode("utf-8"),
            payload_hash=content_hash(payload),
            created_at=datetime.now(UTC),
            published_at=None,
            attempt_count=0,
            last_error=None,
        )
        session.add(record)
        return record

    async def pending(
        self, session: AsyncSession, limit: int = 100
    ) -> list[AgentOutboxRecord]:
        rows = await session.scalars(
            select(AgentOutboxRecord)
            .where(AgentOutboxRecord.published_at.is_(None))
            .order_by(AgentOutboxRecord.created_at, AgentOutboxRecord.event_id)
            .limit(limit)
        )
        return list(rows)

    async def mark_published(self, session: AsyncSession, event_id: str) -> bool:
        result = await session.execute(
            update(AgentOutboxRecord)
            .where(
                AgentOutboxRecord.event_id == event_id,
                AgentOutboxRecord.published_at.is_(None),
            )
            .values(
                published_at=datetime.now(UTC),
                attempt_count=AgentOutboxRecord.attempt_count + 1,
                last_error=None,
            )
        )
        assert isinstance(result, CursorResult)

        return result.rowcount == 1

    async def mark_failed(
        self, session: AsyncSession, event_id: str, *, error_code: str
    ) -> bool:
        result = await session.execute(
            update(AgentOutboxRecord)
            .where(
                AgentOutboxRecord.event_id == event_id,
                AgentOutboxRecord.published_at.is_(None),
            )
            .values(
                attempt_count=AgentOutboxRecord.attempt_count + 1,
                last_error=error_code[:500],
            )
        )
        assert isinstance(result, CursorResult)

        return result.rowcount == 1
