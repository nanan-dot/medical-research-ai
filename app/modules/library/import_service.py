"""Safe multi-file import into managed library storage."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path, PureWindowsPath
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.task_service import DocumentTaskService
from app.modules.document_upload.model import DocumentAsset
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library.repository import LibraryRepository
from app.modules.library.schema import LibraryImportItem, LibraryImportRead

_MIME = {
    ".pdf": {"application/pdf", "application/x-pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".md": {"text/markdown", "text/plain"}, ".markdown": {"text/markdown", "text/plain"}, ".txt": {"text/plain"}, ".doc": {"application/msword", "application/octet-stream"},
}


class LibraryImportService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = LibraryRepository(session)

    async def import_files(self, files: Sequence[UploadFile]) -> LibraryImportRead:
        if len(files) > settings.MAX_LIBRARY_IMPORT_FILES:
            return LibraryImportRead(items=[LibraryImportItem(original_filename=file.filename or "", status="rejected", error_code="too_many_files") for file in files])
        items = []
        for file in files:
            items.append(await self._import_one(file))
        return LibraryImportRead(items=items)

    async def _import_one(self, file: UploadFile) -> LibraryImportItem:
        name = file.filename or ""
        try:
            suffix = self._validate_name_and_mime(name, file.content_type)
        except ValueError as exc:
            await file.close()
            return LibraryImportItem(original_filename=name, status="rejected", error_code=str(exc))
        root = settings.UPLOAD_DIR.resolve()
        temporary = root / ".tmp"
        documents = root / "library"
        temporary.mkdir(parents=True, exist_ok=True)
        documents.mkdir(parents=True, exist_ok=True)
        temp_path = temporary / f"{uuid4().hex}.uploading"
        final_path: Path | None = None
        try:
            byte_size, digest, head = await self._stream(file, temp_path)
            self._validate_signature(suffix, head, temp_path)
            duplicate_id = await self._repository.find_asset_document_by_sha256(digest)
            if duplicate_id is not None:
                return LibraryImportItem(original_filename=name, status="duplicate", document_id=duplicate_id, error_code="duplicate_content")
            final_path = documents / f"{uuid4().hex}{suffix}"
            await asyncio.to_thread(shutil.move, str(temp_path), str(final_path))
            document = await self._persist(name, suffix, file.content_type or "application/octet-stream", final_path, byte_size, digest)
            task = await DocumentTaskService(self._session).enqueue(document.id, "reparse")
            return LibraryImportItem(original_filename=name, status="accepted", document_id=document.id, task_id=task.id)
        except ValueError as exc:
            return LibraryImportItem(original_filename=name, status="rejected", error_code=str(exc))
        finally:
            await file.close()
            if temp_path.exists(): temp_path.unlink()
            if final_path is not None and final_path.exists() and self._session.new:
                # A later transaction error cannot leave a managed orphan.
                final_path.unlink()

    @staticmethod
    def _validate_name_and_mime(name: str, media_type: str | None) -> str:
        if not name or Path(name).name != name or PureWindowsPath(name).name != name or len(name) > 255:
            raise ValueError("invalid_filename")
        suffix = Path(name).suffix.casefold()
        if suffix not in _MIME: raise ValueError("unsupported_format")
        if media_type not in _MIME[suffix]: raise ValueError("invalid_mime")
        return suffix

    async def _stream(self, file: UploadFile, path: Path) -> tuple[int, str, bytes]:
        digest, size, head = hashlib.sha256(), 0, b""
        with path.open("xb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > settings.MAX_LIBRARY_UPLOAD_BYTES: raise ValueError("upload_too_large")
                head = (head + chunk)[:16]
                digest.update(chunk); target.write(chunk)
        if not size: raise ValueError("empty_file")
        return size, digest.hexdigest(), head

    @staticmethod
    def _validate_signature(suffix: str, head: bytes, path: Path) -> None:
        if suffix == ".pdf" and not head.startswith(b"%PDF-"): raise ValueError("invalid_signature")
        if suffix in {".docx", ".pptx"}:
            try:
                with ZipFile(path) as archive:
                    if sum(info.file_size for info in archive.infolist()) > settings.MAX_LIBRARY_ARCHIVE_UNCOMPRESSED_BYTES: raise ValueError("archive_too_large")
                    if "[Content_Types].xml" not in archive.namelist(): raise ValueError("invalid_signature")
            except BadZipFile as exc: raise ValueError("invalid_signature") from exc

    async def _persist(self, name: str, suffix: str, media_type: str, path: Path, size: int, digest: str) -> Document:
        source = await self._session.scalar(select(KnowledgeSource).where(KnowledgeSource.normalized_root_path == str(settings.UPLOAD_DIR.resolve()).casefold()))
        if source is None:
            source = KnowledgeSource(name="上传文档", source_type="temporary_import", root_path=str(settings.UPLOAD_DIR.resolve()), normalized_root_path=str(settings.UPLOAD_DIR.resolve()).casefold(), enabled=True, sync_status="idle")
            self._session.add(source); await self._session.flush()
        stat = path.stat()
        document = Document(knowledge_source_id=source.id, file_path=str(path), normalized_file_path=path.relative_to(settings.UPLOAD_DIR.resolve()).as_posix().casefold(), file_hash=digest, file_size=size, modified_time=datetime.fromtimestamp(stat.st_mtime, UTC), modified_time_ns=stat.st_mtime_ns, scan_state="pending", parse_status="pending", index_status="pending")
        self._session.add(document); await self._session.flush()
        self._session.add(DocumentAsset(document_id=document.id, asset_kind="upload", original_filename=name, stored_relative_path=path.relative_to(settings.UPLOAD_DIR.resolve()).as_posix(), media_type=media_type, byte_size=size, sha256=digest, processing_status="queued"))
        await self._session.flush()
        return document
