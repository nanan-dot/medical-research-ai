"""稳定游标阅读历史。"""

import base64
import json
from datetime import UTC, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_reader.constants import DEFAULT_ACTOR_SCOPE
from app.modules.document_reader.errors import ReaderResourceNotFoundError
from app.modules.document_reader.model import ReaderSession
from app.modules.library_item.model import LibraryItem


def encode_cursor(last_seen_at: datetime, session_id: int) -> str:
    payload = json.dumps([last_seen_at.astimezone(UTC).isoformat(), session_id], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        timestamp, session_id = json.loads(raw)
        return datetime.fromisoformat(timestamp), int(session_id)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid history cursor") from exc


class ReaderHistoryService:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self._session = session
        self._actor_scope = actor_scope

    async def list(self, query: str | None, cursor: str | None, limit: int) -> dict[str, object]:
        statement = select(ReaderSession, LibraryItem).join(LibraryItem, ReaderSession.library_item_id == LibraryItem.id).where(ReaderSession.actor_scope == self._actor_scope, ReaderSession.is_history_hidden.is_(False))
        if query:
            statement = statement.where(LibraryItem.title.ilike(f"%{query.strip()}%"))
        if cursor:
            timestamp, session_id = decode_cursor(cursor)
            statement = statement.where(or_(ReaderSession.last_seen_at < timestamp, and_(ReaderSession.last_seen_at == timestamp, ReaderSession.id < session_id)))
        rows = (await self._session.execute(statement.order_by(ReaderSession.last_seen_at.desc(), ReaderSession.id.desc()).limit(limit + 1))).all()
        page = rows[:limit]
        items = [{"session_id": row.id, "paper_item_id": item.id, "title": item.title, "last_page": row.last_page, "last_seen_at": row.last_seen_at, "destination": f"/papers/{item.id}/reading?page={row.last_page}"} for row, item in page]
        next_cursor = encode_cursor(page[-1][0].last_seen_at, page[-1][0].id) if len(rows) > limit and page else None
        return {"items": items, "next_cursor": next_cursor}

    async def hide(self, session_id: int) -> None:
        entity = await self._session.scalar(select(ReaderSession).where(ReaderSession.id == session_id, ReaderSession.actor_scope == self._actor_scope))
        if entity is None:
            raise ReaderResourceNotFoundError("阅读历史不存在")
        entity.is_history_hidden = True
        await self._session.flush()

    async def clear(self) -> None:
        """Hide history entries without touching reading assets or source records."""
        entries = list(
            (
                await self._session.scalars(
                    select(ReaderSession).where(
                        ReaderSession.actor_scope == self._actor_scope,
                        ReaderSession.is_history_hidden.is_(False),
                    )
                )
            ).all()
        )
        for entry in entries:
            entry.is_history_hidden = True
        await self._session.flush()
