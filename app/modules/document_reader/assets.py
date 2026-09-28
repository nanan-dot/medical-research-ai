"""收藏、偏好、书签和疑问写入。"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_reader.constants import DEFAULT_ACTOR_SCOPE
from app.modules.document_reader.errors import (
    ReaderResourceNotFoundError,
    ReaderStateVersionConflictError,
)
from app.modules.document_reader.model import (
    PaperReaderState,
    ReaderBookmark,
    ReaderPreference,
    ReaderQuestion,
)
from app.modules.document_reader.schema import (
    BookmarkCreate,
    PreferenceUpdate,
    QuestionCreate,
    QuestionStatus,
)
from app.modules.library_item.model import LibraryItem


class ReaderAssetService:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self._session = session
        self._actor_scope = actor_scope

    async def favorite(self, item_id: int, value: bool, expected_version: int) -> dict[str, object]:
        if await self._session.get(LibraryItem, item_id) is None:
            raise ReaderResourceNotFoundError("论文不存在")
        entity = await self._session.scalar(select(PaperReaderState).where(PaperReaderState.library_item_id == item_id, PaperReaderState.actor_scope == self._actor_scope))
        if entity is None:
            if expected_version != 1:
                raise ReaderStateVersionConflictError({"is_favorite": False, "version": 1})
            entity = PaperReaderState(actor_scope=self._actor_scope, library_item_id=item_id, is_favorite=value, version=2)
            self._session.add(entity)
        else:
            self._version(entity.version, expected_version, {"is_favorite": entity.is_favorite, "version": entity.version})
            entity.is_favorite = value
            entity.version += 1
        await self._session.flush()
        return {"is_favorite": entity.is_favorite, "version": entity.version}

    async def preference(self, document_id: int, payload: PreferenceUpdate) -> dict[str, object]:
        entity = await self._session.scalar(select(ReaderPreference).where(ReaderPreference.document_id == document_id, ReaderPreference.actor_scope == self._actor_scope))
        if entity is None:
            self._version(1, payload.expected_version, {"version": 1})
            entity = ReaderPreference(actor_scope=self._actor_scope, document_id=document_id, version=1)
            self._session.add(entity)
        else:
            self._version(entity.version, payload.expected_version, {"version": entity.version})
        for field in ("view_mode", "zoom_percent", "left_panel_mode", "left_collapsed", "right_panel_tab", "focus_mode"):
            value = getattr(payload, field)
            if value is not None:
                setattr(entity, field, value)
        entity.version += 1
        entity.updated_at = datetime.now(UTC)
        await self._session.flush()
        return {field: getattr(entity, field) for field in ("view_mode", "zoom_percent", "left_panel_mode", "left_collapsed", "right_panel_tab", "focus_mode", "version")}

    async def bookmark(self, document_id: int, payload: BookmarkCreate) -> dict[str, object]:
        await self._anchor(document_id, payload.source_anchor_id)
        entity = ReaderBookmark(actor_scope=self._actor_scope, document_id=document_id, source_anchor_id=payload.source_anchor_id, label=payload.label, color=payload.color, version=1)
        self._session.add(entity)
        await self._session.flush()
        return {"id": entity.id, "source_anchor_id": entity.source_anchor_id, "version": 1}

    async def delete_bookmark(self, document_id: int, bookmark_id: int, expected_version: int) -> None:
        entity = await self._session.scalar(select(ReaderBookmark).where(ReaderBookmark.id == bookmark_id, ReaderBookmark.document_id == document_id, ReaderBookmark.actor_scope == self._actor_scope, ReaderBookmark.deleted_at.is_(None)))
        if entity is None:
            raise ReaderResourceNotFoundError("书签不存在")
        self._version(entity.version, expected_version, {"version": entity.version})
        entity.deleted_at = datetime.now(UTC)
        entity.version += 1
        await self._session.flush()

    async def question(self, document_id: int, payload: QuestionCreate) -> dict[str, object]:
        await self._anchor(document_id, payload.source_anchor_id)
        entity = ReaderQuestion(actor_scope=self._actor_scope, document_id=document_id, source_anchor_id=payload.source_anchor_id, content=payload.content.strip(), status="open", version=1)
        self._session.add(entity)
        await self._session.flush()
        return {"id": entity.id, "source_anchor_id": entity.source_anchor_id, "content": entity.content, "status": entity.status, "version": 1}

    async def update_question(self, document_id: int, question_id: int, status: QuestionStatus, expected_version: int) -> dict[str, object]:
        entity = await self._session.scalar(select(ReaderQuestion).where(ReaderQuestion.id == question_id, ReaderQuestion.document_id == document_id, ReaderQuestion.actor_scope == self._actor_scope, ReaderQuestion.deleted_at.is_(None)))
        if entity is None:
            raise ReaderResourceNotFoundError("疑问不存在")
        self._version(entity.version, expected_version, {"status": entity.status, "version": entity.version})
        entity.status = status.value
        entity.resolved_at = datetime.now(UTC) if status == QuestionStatus.RESOLVED else None
        entity.version += 1
        await self._session.flush()
        return {"id": entity.id, "status": entity.status, "version": entity.version}

    async def delete_question(self, document_id: int, question_id: int, expected_version: int) -> None:
        entity = await self._session.scalar(select(ReaderQuestion).where(ReaderQuestion.id == question_id, ReaderQuestion.document_id == document_id, ReaderQuestion.actor_scope == self._actor_scope, ReaderQuestion.deleted_at.is_(None)))
        if entity is None:
            raise ReaderResourceNotFoundError("疑问不存在")
        self._version(entity.version, expected_version, {"status": entity.status, "version": entity.version})
        entity.deleted_at = datetime.now(UTC)
        entity.version += 1
        await self._session.flush()

    async def _anchor(self, document_id: int, anchor_id: int) -> None:
        anchor = await self._session.get(DocumentSourceAnchor, anchor_id)
        revision = None if anchor is None else await self._session.get(DocumentAnchorRevision, anchor.anchor_revision_id)
        if anchor is None or revision is None or revision.document_id != document_id:
            raise ReaderResourceNotFoundError("SourceAnchor 不属于该文档")

    @staticmethod
    def _version(current: int, expected: int, state: dict[str, object]) -> None:
        if current != expected:
            raise ReaderStateVersionConflictError(state)
