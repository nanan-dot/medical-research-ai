"""事务外发布、事务内确认的 M0 outbox 发布器。"""

import json
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.agents.hash_schema import content_hash
from app.agents.outbox_service import OutboxService
from app.agents.transaction import ImmediateUnitOfWork

PublishEvent = Callable[[str, str, dict[str, object]], Awaitable[None]]


class OutboxPublisher:
    """下游必须按 event_id 去重；网络调用不会占用写事务。"""

    def __init__(
        self,
        engine: AsyncEngine,
        publish_event: PublishEvent,
        outbox: OutboxService | None = None,
    ) -> None:
        self._engine = engine
        self._publish_event = publish_event
        self._outbox = outbox or OutboxService()

    async def run_once(self, *, limit: int = 100) -> tuple[int, int]:
        async with AsyncSession(self._engine) as session:
            pending = await self._outbox.pending(session, limit=limit)
            envelopes = [
                (row.event_id, row.event_type, row.payload_json, row.payload_hash)
                for row in pending
            ]

        published = 0
        failed = 0
        for event_id, event_type, raw_payload, expected_hash in envelopes:
            try:
                payload = json.loads(raw_payload)
                if (
                    not isinstance(payload, dict)
                    or content_hash(payload) != expected_hash
                ):
                    raise ValueError("outbox_payload_hash_mismatch")
                await self._publish_event(event_id, event_type, payload)
            except Exception as error:  # noqa: BLE001 - persist transport failure
                error_code = (
                    str(error)
                    if isinstance(error, ValueError)
                    else "outbox_publish_failed"
                )
                async with ImmediateUnitOfWork(self._engine) as uow:
                    assert uow.session is not None
                    await self._outbox.mark_failed(
                        uow.session, event_id, error_code=error_code
                    )
                    await uow.commit()
                failed += 1
                continue

            async with ImmediateUnitOfWork(self._engine) as uow:
                assert uow.session is not None
                if await self._outbox.mark_published(uow.session, event_id):
                    published += 1
                await uow.commit()
        return published, failed
