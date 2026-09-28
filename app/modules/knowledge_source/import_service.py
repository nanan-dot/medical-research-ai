"""将单篇 PDF 导入到用户明确指定的知识库。"""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.common.exceptions import ConflictError, NotFoundError
from app.common.path_utils import normalized_path_key
from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document_relocation.file_versions import FileVersionService
from app.modules.document_upload.model import DocumentAsset
from app.modules.document_upload.repository import DocumentAssetRepository
from app.modules.document_upload.service import (
    DocumentUploadService,
    UploadStorageError,
    UploadValidationError,
    _move_file,
    _remove_file_if_exists,
    _safe_descendant,
    _validate_pdf_structure,
)
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.schema import (
    KnowledgeSourceDocumentImportRead,
    KnowledgeSourceSyncStatus,
    KnowledgeSourceType,
)

_IMPORT_ROOT_DIRECTORY = "knowledge-sources"
_TEMPORARY_DIRECTORY = ".tmp"


class KnowledgeSourceDocumentImportService:
    """保存文件、文档和资产，且归属始终由用户显式指定。"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._sources = KnowledgeSourceRepository(session)
        self._documents = DocumentRepository(session)
        self._assets = DocumentAssetRepository(session)

    async def import_document(
        self,
        *,
        file: UploadFile,
        knowledge_source_id: int | None,
        new_source_name: str | None,
        relative_directory: str | None,
    ) -> KnowledgeSourceDocumentImportRead:
        original_filename = DocumentUploadService._validate_file_metadata(file)
        source_name = (new_source_name or "").strip()
        has_existing_source = knowledge_source_id is not None
        has_new_source = bool(source_name)
        if has_existing_source == has_new_source:
            raise UploadValidationError("请且仅选择一个文档归属知识库")

        relative_path = _validate_relative_directory(relative_directory)
        upload_root, temporary_directory = await asyncio.to_thread(
            _prepare_import_directories
        )
        temporary_path = _safe_descendant(
            upload_root, temporary_directory / f"{uuid4().hex}.uploading"
        )
        final_path: Path | None = None
        completed = False
        try:
            byte_size, sha256 = await DocumentUploadService(
                self._session
            )._stream_to_temporary_file(file, temporary_path)
            await asyncio.to_thread(_validate_pdf_structure, temporary_path)

            async with self._session.begin():
                source, _ = await self._resolve_source(
                    upload_root, knowledge_source_id, source_name
                )
                source_root = await asyncio.to_thread(_resolve_source_root, source)
                target_directory = _safe_descendant(
                    source_root, source_root / relative_path
                )
                await asyncio.to_thread(
                    target_directory.mkdir, parents=True, exist_ok=True
                )
                final_path = _safe_descendant(
                    source_root, target_directory / f"{uuid4().hex}.pdf"
                )
                await asyncio.to_thread(_move_file, temporary_path, final_path)
                document, asset = await self._persist_document(
                    source,
                    final_path,
                    original_filename,
                    file.content_type or "application/pdf",
                    byte_size,
                    sha256,
                )

            completed = True
            return KnowledgeSourceDocumentImportRead(
                document_id=document.id,
                knowledge_source_id=source.id,
                original_filename=original_filename,
                stored_relative_path=asset.stored_relative_path,
            )
        except OSError as exc:
            raise UploadStorageError("文档保存失败，请稍后重试") from exc
        finally:
            await asyncio.to_thread(_remove_file_if_exists, temporary_path)
            if final_path is not None and not completed:
                # 事务提交失败和业务校验失败都不能留下孤儿文件。
                await asyncio.to_thread(_remove_file_if_exists, final_path)
            await file.close()

    async def _resolve_source(
        self, upload_root: Path, knowledge_source_id: int | None, source_name: str
    ) -> tuple[KnowledgeSource, Path | None]:
        if knowledge_source_id is not None:
            source = await self._sources.get(knowledge_source_id)
            if source is None:
                raise NotFoundError("所选知识库不存在")
            if not source.enabled:
                raise UploadValidationError("所选知识库已停用")
            return source, None

        existing_sources = await self._sources.list(limit=10_000)
        if any(
            source.name.casefold() == source_name.casefold()
            for source in existing_sources
        ):
            raise ConflictError("知识库名称已存在")
        root_path = _safe_descendant(
            upload_root, upload_root / _IMPORT_ROOT_DIRECTORY / uuid4().hex
        )
        await asyncio.to_thread(root_path.mkdir, parents=True, exist_ok=False)
        source = KnowledgeSource(
            name=source_name,
            # 用户命名创建的知识库是普通可见来源（本地文件夹），
            # 不是临时导入来源——后者会显示"临时导入"标签且语义不符。
            source_type=KnowledgeSourceType.LOCAL_FOLDER.value,
            root_path=str(root_path),
            normalized_root_path=normalized_path_key(root_path),
            sync_status=KnowledgeSourceSyncStatus.IDLE.value,
        )
        return await self._sources.create(source), root_path

    async def _persist_document(
        self,
        source: KnowledgeSource,
        final_path: Path,
        original_filename: str,
        media_type: str,
        byte_size: int,
        sha256: str,
    ) -> tuple[Document, DocumentAsset]:
        stat = await asyncio.to_thread(final_path.stat)
        # 资料夹可位于任意已授权磁盘；资产路径以来源 ID 命名，保证全局唯一。
        stored_relative_path = f"knowledge-sources/{source.id}/{final_path.name}"
        document = Document(
            knowledge_source_id=source.id,
            file_path=str(final_path),
            normalized_file_path=os.path.normcase(os.path.normpath(str(final_path))),
            file_hash=sha256,
            file_size=byte_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            modified_time_ns=stat.st_mtime_ns,
            scan_state="pending",
            parse_status="pending",
            index_status="pending",
        )
        await self._documents.create(document)
        await FileVersionService(self._session).observe(
            document, content_available=True
        )
        asset = DocumentAsset(
            document=document,
            asset_kind="upload",
            original_filename=original_filename,
            stored_relative_path=stored_relative_path,
            media_type=media_type,
            byte_size=byte_size,
            sha256=sha256,
            processing_status="pending_parse",
        )
        return document, await self._assets.create(asset)


def _prepare_import_directories() -> tuple[Path, Path]:
    upload_root = settings.UPLOAD_DIR.expanduser()
    upload_root.mkdir(parents=True, exist_ok=True)
    resolved_root = upload_root.resolve(strict=True)
    temporary_directory = _safe_descendant(
        resolved_root, resolved_root / _TEMPORARY_DIRECTORY
    )
    temporary_directory.mkdir(exist_ok=True)
    return resolved_root, temporary_directory.resolve(strict=True)


def _resolve_source_root(source: KnowledgeSource) -> Path:
    source_root = Path(source.root_path).expanduser()
    if not source_root.exists() or not source_root.is_dir():
        raise UploadStorageError("所选知识库目录不可用")
    return source_root.resolve(strict=True)


def _validate_relative_directory(value: str | None) -> Path:
    directory = (value or "").strip()
    if not directory:
        return Path(".")
    windows_path = PureWindowsPath(directory)
    posix_path = PurePosixPath(directory)
    if (
        "\\" in directory
        or windows_path.drive
        or windows_path.root
        or posix_path.is_absolute()
        or any(part in {"", ".", ".."} for part in posix_path.parts)
    ):
        raise UploadValidationError("逻辑子目录必须是安全的相对路径")
    return Path(*posix_path.parts)
