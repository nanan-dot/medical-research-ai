"""受控文件定位与文档预览编排。"""

from __future__ import annotations

import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AppError, ConflictError, NotFoundError
from app.common.path_utils import is_within_root
from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document_preview.docx_converter import convert_docx_to_preview
from app.modules.document_preview.schema import DocumentPreviewKind, DocumentPreviewRead
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.repository import KnowledgeSourceRepository


class DocumentPreviewUnavailableError(ConflictError):
    code = "document_preview_unavailable"


class DocumentPreviewTooLargeError(AppError):
    status_code = 413
    code = "document_preview_too_large"


class DocumentPreviewService:
    """将文档 ID 映射到受信任根目录内的真实文件，绝不接受外部路径。"""

    def __init__(self, session: AsyncSession):
        self._documents = DocumentRepository(session)
        self._sources = KnowledgeSourceRepository(session)

    async def get_preview(self, document_id: int) -> DocumentPreviewRead:
        document, path = await self._get_document_path(document_id)
        suffix = path.suffix.casefold()
        if suffix == ".pdf":
            return DocumentPreviewRead(
                document_id=document.id,
                kind=DocumentPreviewKind.PDF,
                content_url=f"/api/v1/documents/{document.id}/original",
            )
        if suffix == ".docx":
            await self._ensure_docx_preview_size(path)
            blocks, tables = await asyncio.to_thread(convert_docx_to_preview, str(path))
            return DocumentPreviewRead(
                document_id=document.id,
                kind=DocumentPreviewKind.DOCX,
                blocks=blocks,
                tables=tables,
            )
        return DocumentPreviewRead(
            document_id=document.id,
            kind=DocumentPreviewKind.UNAVAILABLE,
            message="该文件格式暂不支持在线预览。",
        )

    async def get_pdf_path(self, document_id: int) -> Path:
        _, path = await self._get_document_path(document_id)
        if path.suffix.casefold() != ".pdf":
            raise DocumentPreviewUnavailableError("该文件不是可在线预览的 PDF")
        return path

    async def _get_document_path(self, document_id: int) -> tuple[Document, Path]:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("文档不存在")
        source = await self._sources.get(document.knowledge_source_id)
        if source is None:
            raise DocumentPreviewUnavailableError("文档知识源不可用")
        path = await asyncio.to_thread(_resolve_source_file, source, document)
        return document, path

    async def _ensure_docx_preview_size(self, path: Path) -> None:
        byte_size = await asyncio.to_thread(path.stat)
        if byte_size.st_size > settings.MAX_DOCX_PREVIEW_BYTES:
            raise DocumentPreviewTooLargeError("DOCX 文件超过在线预览大小限制")


def _resolve_source_file(source: KnowledgeSource, document: Document) -> Path:
    """以可信知识源根目录为锚点解析路径，并拒绝记录损坏后的路径逃逸。"""

    try:
        root = Path(source.root_path).resolve(strict=True)
        stored_path = Path(document.file_path)
        candidate = stored_path if stored_path.is_absolute() else root / stored_path
        resolved_path = candidate.resolve(strict=True)
    except OSError as exc:
        raise DocumentPreviewUnavailableError("原始文件当前不可用") from exc
    if not resolved_path.is_file() or not is_within_root(resolved_path, root):
        raise DocumentPreviewUnavailableError("原始文件不在受控知识源目录内")
    return resolved_path
