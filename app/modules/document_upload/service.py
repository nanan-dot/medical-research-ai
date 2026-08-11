"""单 PDF 上传业务编排。"""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.common.exceptions import AppError
from app.common.path_utils import normalized_path_key
from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import DocumentRead
from app.modules.document_upload.model import DocumentAsset
from app.modules.document_upload.repository import DocumentAssetRepository
from app.modules.document_upload.schema import DocumentAssetRead, DocumentUploadRead
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.schema import (
    KnowledgeSourceSyncStatus,
    KnowledgeSourceType,
)

_ALLOWED_MEDIA_TYPES = frozenset({"application/pdf", "application/x-pdf"})
_PDF_SIGNATURE = b"%PDF-"
_STREAM_CHUNK_BYTES = 1024 * 1024
_STORAGE_DIRECTORY_NAME = "documents"
_TEMPORARY_DIRECTORY_NAME = ".tmp"
_UPLOAD_SOURCE_NAME = "上传文档"


class UploadValidationError(AppError):
    status_code = 400
    code = "invalid_pdf_upload"


class UploadTooLargeError(AppError):
    status_code = 413
    code = "pdf_upload_too_large"


class UploadStorageError(AppError):
    status_code = 422
    code = "pdf_upload_storage_failed"


class DocumentUploadService:
    """将单个 PDF 安全地持久化，并建立文档与资产的一对一关系。"""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._documents = DocumentRepository(session)
        self._assets = DocumentAssetRepository(session)
        self._sources = KnowledgeSourceRepository(session)

    async def upload(self, file: UploadFile) -> DocumentUploadRead:
        original_filename = self._validate_file_metadata(file)
        upload_root, temporary_directory, documents_directory = await asyncio.to_thread(
            _prepare_storage_directories
        )
        temporary_path = _safe_descendant(
            upload_root,
            temporary_directory / f"{uuid4().hex}.uploading",
        )
        final_path: Path | None = None

        try:
            byte_size, sha256 = await self._stream_to_temporary_file(file, temporary_path)
            await asyncio.to_thread(_validate_pdf_structure, temporary_path)

            final_path = _safe_descendant(
                upload_root,
                documents_directory / f"{uuid4().hex}.pdf",
            )
            await asyncio.to_thread(_move_file, temporary_path, final_path)

            document, asset = await self._persist_uploaded_asset(
                upload_root=upload_root,
                final_path=final_path,
                original_filename=original_filename,
                media_type=file.content_type or "application/pdf",
                byte_size=byte_size,
                sha256=sha256,
            )
            return DocumentUploadRead(
                document=DocumentRead.model_validate(document),
                asset=DocumentAssetRead.model_validate(asset),
                parse_trigger_url=f"/api/v1/documents/{document.id}/parse",
            )
        except AppError:
            await asyncio.to_thread(_remove_file_if_exists, temporary_path)
            if final_path is not None:
                await asyncio.to_thread(_remove_file_if_exists, final_path)
            raise
        except OSError as exc:
            await asyncio.to_thread(_remove_file_if_exists, temporary_path)
            if final_path is not None:
                await asyncio.to_thread(_remove_file_if_exists, final_path)
            raise UploadStorageError("PDF 文件保存失败，请稍后重试") from exc
        except Exception:
            await asyncio.to_thread(_remove_file_if_exists, temporary_path)
            if final_path is not None:
                await asyncio.to_thread(_remove_file_if_exists, final_path)
            raise
        finally:
            await file.close()

    async def _stream_to_temporary_file(
        self,
        file: UploadFile,
        temporary_path: Path,
    ) -> tuple[int, str]:
        digest = hashlib.sha256()
        byte_size = 0
        leading_bytes = b""

        try:
            with temporary_path.open("xb") as destination:
                while chunk := await file.read(_STREAM_CHUNK_BYTES):
                    byte_size += len(chunk)
                    if byte_size > settings.MAX_UPLOAD_PDF_BYTES:
                        raise UploadTooLargeError(
                            f"单个 PDF 不得超过 {settings.MAX_UPLOAD_PDF_BYTES // (1024 * 1024)} MiB"
                        )
                    if len(leading_bytes) < len(_PDF_SIGNATURE):
                        leading_bytes += chunk[: len(_PDF_SIGNATURE) - len(leading_bytes)]
                    digest.update(chunk)
                    destination.write(chunk)
        except UploadTooLargeError:
            raise
        except OSError as exc:
            raise UploadStorageError("无法写入临时上传文件") from exc

        if byte_size == 0 or not leading_bytes.startswith(_PDF_SIGNATURE):
            raise UploadValidationError("文件内容不是有效的 PDF")
        return byte_size, digest.hexdigest()

    async def _persist_uploaded_asset(
        self,
        *,
        upload_root: Path,
        final_path: Path,
        original_filename: str,
        media_type: str,
        byte_size: int,
        sha256: str,
    ) -> tuple[Document, DocumentAsset]:
        relative_path = final_path.relative_to(upload_root).as_posix()
        modified_time = datetime.fromtimestamp(final_path.stat().st_mtime, tz=UTC)

        async with self._session.begin():
            source = await self._get_or_create_upload_source(upload_root)
            document = Document(
                knowledge_source_id=source.id,
                file_path=str(final_path),
                normalized_file_path=os.path.normcase(os.path.normpath(relative_path)),
                file_hash=sha256,
                file_size=byte_size,
                modified_time=modified_time,
                modified_time_ns=final_path.stat().st_mtime_ns,
                scan_state="pending",
                parse_status="pending",
                index_status="pending",
            )
            await self._documents.create(document)
            asset = DocumentAsset(
                document=document,
                asset_kind="upload",
                original_filename=original_filename,
                stored_relative_path=relative_path,
                media_type=media_type,
                byte_size=byte_size,
                sha256=sha256,
                processing_status="pending_parse",
            )
            await self._assets.create(asset)
        return document, asset

    async def _get_or_create_upload_source(self, upload_root: Path) -> KnowledgeSource:
        normalized_root_path = normalized_path_key(upload_root)
        source = await self._sources.get_by_normalized_path(normalized_root_path)
        if source is not None:
            return source

        source = KnowledgeSource(
            name=_UPLOAD_SOURCE_NAME,
            source_type=KnowledgeSourceType.TEMPORARY_IMPORT.value,
            root_path=str(upload_root),
            normalized_root_path=normalized_root_path,
            sync_status=KnowledgeSourceSyncStatus.IDLE.value,
        )
        return await self._sources.create(source)

    @staticmethod
    def _validate_file_metadata(file: UploadFile) -> str:
        original_filename = file.filename or ""
        if not original_filename:
            raise UploadValidationError("请上传一个 PDF 文件")
        if (
            Path(original_filename).name != original_filename
            or PureWindowsPath(original_filename).name != original_filename
            or len(original_filename) > 255
        ):
            raise UploadValidationError("文件名不合法")
        if Path(original_filename).suffix.lower() != ".pdf":
            raise UploadValidationError("仅支持 PDF 文件")
        if file.content_type not in _ALLOWED_MEDIA_TYPES:
            raise UploadValidationError("文件 MIME 类型必须为 application/pdf")
        return original_filename


def _prepare_storage_directories() -> tuple[Path, Path, Path]:
    """先解析真实根目录，再构造受限子路径，阻断配置和符号链接造成的越界。"""

    upload_root = settings.UPLOAD_DIR.expanduser()
    upload_root.mkdir(parents=True, exist_ok=True)
    resolved_root = upload_root.resolve(strict=True)
    temporary_directory = _safe_descendant(
        resolved_root,
        resolved_root / _TEMPORARY_DIRECTORY_NAME,
    )
    documents_directory = _safe_descendant(
        resolved_root,
        resolved_root / _STORAGE_DIRECTORY_NAME,
    )
    temporary_directory.mkdir(exist_ok=True)
    documents_directory.mkdir(exist_ok=True)
    return resolved_root, temporary_directory.resolve(strict=True), documents_directory.resolve(strict=True)


def _safe_descendant(root: Path, candidate: Path) -> Path:
    resolved_candidate = candidate.resolve(strict=False)
    try:
        resolved_candidate.relative_to(root)
    except ValueError as exc:
        raise UploadStorageError("上传文件路径越界") from exc
    return resolved_candidate


def _validate_pdf_structure(path: Path) -> None:
    try:
        reader = PdfReader(str(path), strict=True)
        if reader.is_encrypted:
            raise UploadValidationError("暂不支持加密 PDF")
        if len(reader.pages) == 0:
            raise UploadValidationError("PDF 不包含可读取页面")
    except UploadValidationError:
        raise
    except Exception as exc:
        raise UploadValidationError("PDF 文件损坏或结构无效") from exc


def _move_file(source: Path, destination: Path) -> None:
    shutil.move(str(source), str(destination))


def _remove_file_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()
