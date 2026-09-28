"""阅读器表的 SQLAlchemy 数据访问。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_reader.model import ReaderPageExposure, ReaderSession


class ReaderRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_session(self, session_id: int, actor_scope: str) -> ReaderSession | None:
        return await self._session.scalar(select(ReaderSession).where(ReaderSession.id == session_id, ReaderSession.actor_scope == actor_scope))

    async def active_session(
        self,
        library_item_id: int,
        device_id: str,
        actor_scope: str,
        document_file_hash: str,
    ) -> ReaderSession | None:
        """Return only a resumable session for the current immutable PDF file."""
        statement = select(ReaderSession).where(
            ReaderSession.library_item_id == library_item_id,
            ReaderSession.device_id == device_id,
            ReaderSession.actor_scope == actor_scope,
            ReaderSession.document_file_hash == document_file_hash,
            ReaderSession.status.in_(("active", "idle")),
        )
        return await self._session.scalar(statement.order_by(ReaderSession.id.desc()))

    async def session_by_idempotency_key(self, key: str, actor_scope: str) -> ReaderSession | None:
        return await self._session.scalar(select(ReaderSession).where(ReaderSession.idempotency_key == key, ReaderSession.actor_scope == actor_scope))

    async def exposure(self, session_id: int, page_number: int) -> ReaderPageExposure | None:
        return await self._session.scalar(select(ReaderPageExposure).where(ReaderPageExposure.session_id == session_id, ReaderPageExposure.page_number == page_number))

    async def exposures_for_item(
        self, library_item_id: int, actor_scope: str, document_file_hash: str
    ) -> list[ReaderPageExposure]:
        rows = await self._session.scalars(
            select(ReaderPageExposure)
            .join(ReaderSession)
            .where(
                ReaderSession.library_item_id == library_item_id,
                ReaderSession.actor_scope == actor_scope,
                ReaderSession.document_file_hash == document_file_hash,
            )
        )
        return list(rows.all())

    async def save(self, entity: object) -> None:
        self._session.add(entity)
        await self._session.flush()
