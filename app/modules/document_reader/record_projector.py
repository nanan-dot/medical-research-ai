"""高亮、批注、疑问、书签统一只读投影。"""

from __future__ import annotations

import base64
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_anchor.model import (
    DocumentAnchorFragment,
    DocumentAnchorRevision,
    DocumentSourceAnchor,
    DocumentSourcePage,
)
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_layout.model import (
    DocumentLayoutSection,
    DocumentSegmentationRevision,
)
from app.modules.document_reader.constants import (
    DEFAULT_ACTOR_SCOPE,
    RECORD_COUNTING_POLICY_VERSION,
)
from app.modules.document_reader.model import ReaderBookmark, ReaderQuestion
from app.modules.document_reader.records import (
    classify_annotation,
    filter_record_items,
    summarize_record_items,
)


class ReaderRecordProjector:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self._session = session
        self._actor_scope = actor_scope

    async def list_records(
        self,
        document_id: int,
        *,
        record_type: str | None,
        section_id: int | None,
        query: str | None,
        cursor: str | None,
        limit: int,
    ) -> dict[str, object]:
        records = await self._all(document_id)
        filtered = filter_record_items(
            records, record_type=record_type, section_id=section_id, query=query
        )
        page = self._page(filtered, cursor, limit)
        return {
            "items": page[0],
            "next_cursor": page[1],
            "counting_policy_version": RECORD_COUNTING_POLICY_VERSION,
        }

    async def summary(
        self,
        document_id: int,
        *,
        record_type: str | None,
        section_id: int | None,
        query: str | None,
    ) -> dict[str, object]:
        filtered = filter_record_items(
            await self._all(document_id),
            record_type=record_type,
            section_id=section_id,
            query=query,
        )
        return {
            "counts": summarize_record_items(filtered),
            "total": len(filtered),
            "counting_policy_version": RECORD_COUNTING_POLICY_VERSION,
        }

    async def _all(self, document_id: int) -> list[dict[str, object]]:
        anchors = await self._anchors(document_id)
        sections = await self._sections(document_id)
        records: list[dict[str, object]] = []
        annotations = list((await self._session.scalars(select(DocumentAnnotation).where(DocumentAnnotation.document_id == document_id, DocumentAnnotation.deleted_at.is_(None)))).all())
        for annotation in annotations:
            anchor = anchors.get(annotation.source_anchor_id) if annotation.source_anchor_id else None
            records.append(self._record(f"annotation:{annotation.id}", classify_annotation(annotation.note), annotation.source_anchor_id, annotation.selected_text, annotation.note, annotation.page_number, annotation.created_at, anchor, sections))
        questions = list((await self._session.scalars(select(ReaderQuestion).where(ReaderQuestion.document_id == document_id, ReaderQuestion.actor_scope == self._actor_scope, ReaderQuestion.deleted_at.is_(None)))).all())
        for question in questions:
            anchor = anchors.get(question.source_anchor_id)
            records.append(self._record(f"question:{question.id}", "question", question.source_anchor_id, anchor[0] if anchor else "", question.content, anchor[1] if anchor else None, question.created_at, anchor, sections))
        bookmarks = list((await self._session.scalars(select(ReaderBookmark).where(ReaderBookmark.document_id == document_id, ReaderBookmark.actor_scope == self._actor_scope, ReaderBookmark.deleted_at.is_(None)))).all())
        for bookmark in bookmarks:
            anchor = anchors.get(bookmark.source_anchor_id)
            records.append(self._record(f"bookmark:{bookmark.id}", "bookmark", bookmark.source_anchor_id, anchor[0] if anchor else "", bookmark.label, anchor[1] if anchor else None, bookmark.created_at, anchor, sections))
        return sorted(records, key=lambda row: (str(row["created_at"]), str(row["record_id"])), reverse=True)

    async def _anchors(self, document_id: int) -> dict[int, tuple[str, int, str]]:
        rows = (await self._session.execute(select(DocumentSourceAnchor.id, DocumentSourceAnchor.quote, DocumentSourcePage.page_number, DocumentSourceAnchor.resolution_status).join(DocumentAnchorFragment, DocumentAnchorFragment.anchor_id == DocumentSourceAnchor.id).join(DocumentSourcePage, DocumentSourcePage.id == DocumentAnchorFragment.page_id).join(DocumentAnchorRevision, DocumentAnchorRevision.id == DocumentSourceAnchor.anchor_revision_id).where(DocumentAnchorRevision.document_id == document_id).order_by(DocumentAnchorFragment.fragment_order))).all()
        return {anchor_id: (quote, page, status) for anchor_id, quote, page, status in rows}

    async def _sections(self, document_id: int) -> list[DocumentLayoutSection]:
        """Use the published layout only; old anchors deliberately remain relocatable."""
        statement = (
            select(DocumentLayoutSection)
            .join(
                DocumentSegmentationRevision,
                DocumentLayoutSection.segmentation_revision_id
                == DocumentSegmentationRevision.id,
            )
            .join(
                DocumentAnchorRevision,
                DocumentSegmentationRevision.anchor_revision_id
                == DocumentAnchorRevision.id,
            )
            .where(
                DocumentAnchorRevision.document_id == document_id,
                DocumentAnchorRevision.state.in_(("ready", "review_required")),
                DocumentSegmentationRevision.state.in_(("ready", "review_required")),
            )
            .order_by(DocumentLayoutSection.level.desc(), DocumentLayoutSection.id)
        )
        return list((await self._session.scalars(statement)).all())

    @staticmethod
    def _page(
        records: list[dict[str, object]], cursor: str | None, limit: int
    ) -> tuple[list[dict[str, object]], str | None]:
        start = 0
        if cursor:
            created_at, record_id = _decode_cursor(cursor)
            for index, record in enumerate(records):
                if (str(record["created_at"]), str(record["record_id"])) < (
                    created_at,
                    record_id,
                ):
                    start = index
                    break
            else:
                return [], None
        page = records[start : start + limit]
        next_cursor = (
            _encode_cursor(str(page[-1]["created_at"]), str(page[-1]["record_id"]))
            if len(records) > start + limit and page
            else None
        )
        return page, next_cursor

    @staticmethod
    def _record(record_id: str, record_type: str, source_anchor_id: int | None, quote: str, text: str | None, page: int | None, created_at: object, anchor: tuple[str, int, str] | None, sections: list[DocumentLayoutSection]) -> dict[str, object]:
        section = next(
            (item for item in sections if page is not None and item.first_page <= page <= item.last_page),
            None,
        )
        return {"record_id": record_id, "record_type": record_type, "source_anchor_id": source_anchor_id, "quote": quote, "text": text, "page_number": page, "section_id": section.id if section else None, "section_path": [section.literal_title] if section else [], "created_at": created_at, "relocation_status": anchor[2] if anchor else "relocation_required", "locate_target": {"source_anchor_id": source_anchor_id, "page_number": page} if anchor else None}


def _encode_cursor(created_at: str, record_id: str) -> str:
    payload = json.dumps([created_at, record_id], separators=(",", ":"))
    return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, str]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        created_at, record_id = json.loads(raw)
        datetime.fromisoformat(created_at)
        return str(created_at), str(record_id)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid record cursor") from exc
