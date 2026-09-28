"""Atomic source-anchor and business writes, scoped idempotent retries."""

import json

from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_annotation.schema import (
    AnchoredAnnotationCreate,
    AnnotationRead,
)
from app.modules.document_annotation.service import DocumentAnnotationService
from app.modules.document_preview.service import DocumentPreviewService
from app.modules.document_relocation.model import AssetAnchorLink
from app.modules.document_selection.errors import SelectionError
from app.modules.document_selection.model import DocumentReadingNote, SelectionOperation
from app.modules.document_selection.schema import (
    AnchorRead,
    AnchorReference,
    ReadingNoteCreate,
    ReadingNoteRead,
)
from app.modules.document_selection.service import SourceAnchorService, digest


class AnchoredAssetService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._anchors = SourceAnchorService(session)

    async def _existing(
        self, document_id: int, operation: str, key: str, payload: BaseModel
    ) -> tuple[SelectionOperation | None, str]:
        if not key or len(key) > 128:
            raise SelectionError(
                "IDEMPOTENCY_KEY_REQUIRED", "需要有效的 Idempotency-Key"
            )
        await AnchorQueries(self._session).authorized_document(document_id, fresh=True)
        # 先获取文档行写锁，再查幂等记录；并发同键不会分别创建资产。
        await self._session.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(file_hash=Document.file_hash)
        )
        request_hash = digest(
            json.dumps([document_id, payload.model_dump(mode="json")], sort_keys=True)
        )
        existing = await self._session.scalar(
            select(SelectionOperation).where(
                SelectionOperation.scope == "local",
                SelectionOperation.operation == operation,
                SelectionOperation.idempotency_key == key,
            )
        )
        if existing and existing.request_hash != request_hash:
            raise SelectionError("IDEMPOTENCY_KEY_REUSED")
        return existing, request_hash

    async def _anchor(self, document_id: int, reference: AnchorReference) -> AnchorRead:
        if reference.anchor_descriptor is not None:
            return await self._anchors.create(document_id, reference.anchor_descriptor)
        assert reference.source_anchor_id is not None
        return await self._anchors.get(
            reference.source_anchor_id, document_id, require_current=True
        )

    async def annotation(
        self, document_id: int, payload: AnchoredAnnotationCreate, key: str
    ) -> AnnotationRead:
        async with self._session.begin_nested():
            previous, request_hash = await self._existing(
                document_id, "annotation", key, payload
            )
            if previous:
                return AnnotationRead.model_validate_json(previous.response_json)
            await DocumentPreviewService(self._session).get_pdf_path(document_id)
            anchor = await self._anchor(document_id, payload)
            first = anchor.fragments[0]
            annotation = DocumentAnnotation(
                document_id=document_id,
                source_anchor_id=anchor.id,
                file_hash=anchor.file_hash,
                page_number=first.page_number,
                selection_geometry=json.dumps(
                    [rect.model_dump() for rect in first.rectangles]
                ),
                selected_text=anchor.quote,
                selected_text_hash=anchor.quote_hash,
                color=payload.color.value,
                note=payload.note,
            )
            self._session.add(annotation)
            await self._session.flush()
            self._link("document_annotation", annotation.id, anchor.id)
            await self._session.refresh(annotation)
            result = DocumentAnnotationService._to_read(
                annotation, anchor.file_hash, anchor.id
            )
            self._record("annotation", key, request_hash, result)
        return result

    async def note(
        self, document_id: int, payload: ReadingNoteCreate, key: str
    ) -> ReadingNoteRead:
        async with self._session.begin_nested():
            previous, request_hash = await self._existing(
                document_id, "note", key, payload
            )
            if previous:
                return ReadingNoteRead.model_validate_json(previous.response_json)
            anchor = await self._anchor(document_id, payload)
            note = DocumentReadingNote(
                document_id=document_id,
                source_anchor_id=anchor.id,
                content=payload.content,
                quote_snapshot=anchor.quote,
            )
            self._session.add(note)
            await self._session.flush()
            self._link("document_reading_note", note.id, anchor.id)
            await self._session.refresh(note)
            result = ReadingNoteRead(
                id=note.id,
                source_anchor_id=note.source_anchor_id,
                resolved_source_anchor_id=anchor.id,
                content=note.content,
                quote=note.quote_snapshot,
                created_at=note.created_at,
            )
            self._record("note", key, request_hash, result)
        return result

    async def notes(self, document_id: int) -> list[ReadingNoteRead]:
        await AnchorQueries(self._session).authorized_document(document_id)
        rows = list(
            (
                await self._session.scalars(
                    select(DocumentReadingNote)
                    .where(DocumentReadingNote.document_id == document_id)
                    .order_by(DocumentReadingNote.id)
                )
            ).all()
        )
        links = (
            list(
                (
                    await self._session.scalars(
                        select(AssetAnchorLink).where(
                            AssetAnchorLink.asset_type == "document_reading_note",
                            AssetAnchorLink.asset_id.in_([row.id for row in rows]),
                        )
                    )
                ).all()
            )
            if rows
            else []
        )
        resolved = {link.asset_id: link.resolved_anchor_id for link in links}
        return [
            ReadingNoteRead(
                id=row.id,
                source_anchor_id=row.source_anchor_id,
                resolved_source_anchor_id=resolved.get(row.id),
                content=row.content,
                quote=row.quote_snapshot,
                created_at=row.created_at,
            )
            for row in rows
        ]

    def _record(
        self, operation: str, key: str, request_hash: str, response: BaseModel
    ) -> None:
        self._session.add(
            SelectionOperation(
                scope="local",
                operation=operation,
                idempotency_key=key,
                request_hash=request_hash,
                response_json=response.model_dump_json(),
            )
        )

    def _link(self, asset_type: str, asset_id: int, anchor_id: int) -> None:
        """Record immutable provenance separately from a future resolved location."""
        self._session.add(
            AssetAnchorLink(
                asset_type=asset_type,
                asset_id=asset_id,
                original_anchor_id=anchor_id,
                resolved_anchor_id=anchor_id,
                resolution_status="anchored_exact",
                resolution_version=1,
            )
        )
