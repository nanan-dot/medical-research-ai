"""PDF 批注的版本锚定与业务编排。"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import ParseStatus
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_annotation.repository import DocumentAnnotationRepository
from app.modules.document_annotation.schema import (
    AnnotationColor,
    AnnotationCreate,
    AnnotationRead,
    AnnotationUpdate,
    AnnotationVersionStatus,
)
from app.modules.document_preview.service import DocumentPreviewService


class AnnotationVersionConflictError(ConflictError):
    code = "annotation_version_conflict"


class AnnotationUnsupportedDocumentError(ConflictError):
    code = "annotation_unsupported_document"


class DocumentAnnotationService:
    """批注写入以当前文件哈希为前置条件，避免旧页坐标映射到新版本。"""

    def __init__(self, session: AsyncSession):
        self._documents = DocumentRepository(session)
        self._annotations = DocumentAnnotationRepository(session)
        self._previews = DocumentPreviewService(session)

    async def list(self, document_id: int) -> list[AnnotationRead]:
        document = await self._get_document(document_id)
        annotations = await self._annotations.list_active(document_id)
        return [self._to_read(annotation, document.file_hash) for annotation in annotations]

    async def create(
        self,
        document_id: int,
        payload: AnnotationCreate,
    ) -> AnnotationRead:
        document = await self._get_annotatable_document(document_id)
        self._ensure_expected_hash(document, payload.expected_file_hash)
        annotation = DocumentAnnotation(
            document_id=document.id,
            file_hash=document.file_hash,
            page_number=payload.page_number,
            selection_geometry=json.dumps(
                [rectangle.model_dump() for rectangle in payload.rectangles],
                separators=(",", ":"),
            ),
            selected_text=payload.selected_text,
            selected_text_hash=_selection_hash(payload.selected_text),
            color=payload.color.value,
            note=payload.note,
        )
        annotation = await self._annotations.create(annotation)
        return self._to_read(annotation, document.file_hash)

    async def update(
        self,
        document_id: int,
        annotation_id: int,
        payload: AnnotationUpdate,
    ) -> AnnotationRead:
        document = await self._get_annotatable_document(document_id)
        self._ensure_expected_hash(document, payload.expected_file_hash)
        annotation = await self._get_annotation(document_id, annotation_id)
        self._ensure_annotation_current(annotation, document)
        if payload.color is not None:
            annotation.color = payload.color.value
        if "note" in payload.model_fields_set:
            annotation.note = payload.note
        annotation = await self._annotations.save(annotation)
        return self._to_read(annotation, document.file_hash)

    async def delete(
        self,
        document_id: int,
        annotation_id: int,
        expected_file_hash: str,
    ) -> None:
        document = await self._get_annotatable_document(document_id)
        self._ensure_expected_hash(document, expected_file_hash)
        annotation = await self._get_annotation(document_id, annotation_id)
        self._ensure_annotation_current(annotation, document)
        annotation.deleted_at = datetime.now(UTC)
        await self._annotations.save(annotation)

    async def _get_annotatable_document(self, document_id: int) -> Document:
        document = await self._get_document(document_id)
        if document.parse_status != ParseStatus.SUCCEEDED.value:
            raise AnnotationUnsupportedDocumentError("仅已成功解析的 PDF 可添加批注")
        await self._previews.get_pdf_path(document_id)
        return document

    async def _get_document(self, document_id: int) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("文档不存在")
        return document

    async def _get_annotation(
        self,
        document_id: int,
        annotation_id: int,
    ) -> DocumentAnnotation:
        annotation = await self._annotations.get_active(document_id, annotation_id)
        if annotation is None:
            raise NotFoundError("批注不存在")
        return annotation

    @staticmethod
    def _ensure_expected_hash(document: Document, expected_file_hash: str) -> None:
        if document.file_hash != expected_file_hash:
            raise AnnotationVersionConflictError("文档版本已变化，请重新定位批注")

    @staticmethod
    def _ensure_annotation_current(
        annotation: DocumentAnnotation,
        document: Document,
    ) -> None:
        if annotation.file_hash != document.file_hash:
            raise AnnotationVersionConflictError("批注属于旧文档版本，请重新定位")

    @staticmethod
    def _to_read(annotation: DocumentAnnotation, current_file_hash: str) -> AnnotationRead:
        return AnnotationRead(
            id=annotation.id,
            document_id=annotation.document_id,
            file_hash=annotation.file_hash,
            page_number=annotation.page_number,
            rectangles=json.loads(annotation.selection_geometry),
            selected_text=annotation.selected_text,
            selected_text_hash=annotation.selected_text_hash,
            color=cast(AnnotationColor, annotation.color),
            note=annotation.note,
            version_status=(
                AnnotationVersionStatus.CURRENT
                if annotation.file_hash == current_file_hash
                else AnnotationVersionStatus.RELOCATION_REQUIRED
            ),
            created_at=annotation.created_at,
            updated_at=annotation.updated_at,
        )


def _selection_hash(selected_text: str) -> str:
    return hashlib.sha256(selected_text.encode("utf-8")).hexdigest()
