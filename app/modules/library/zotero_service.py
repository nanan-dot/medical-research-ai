"""Persist Zotero source identities and apply mocked/official incremental pages."""

from __future__ import annotations

import inspect
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path, PureWindowsPath
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.task_service import DocumentTaskService
from app.modules.document_upload.model import DocumentAsset
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library.model import ZoteroCollection, ZoteroLibrary
from app.modules.library.schema import ZoteroSourceCreate
from app.modules.library.zotero import ZoteroAttachment, ZoteroIncrementalResult

_ZOTERO_ATTACHMENT_TYPES = {
    ".pdf": {"application/pdf", "application/x-pdf"},
    ".docx": {"application/vnd.openxmlformats-officedocument.wordprocessingml.document"},
    ".pptx": {"application/vnd.openxmlformats-officedocument.presentationml.presentation"},
    ".md": {"text/markdown", "text/plain"},
    ".markdown": {"text/markdown", "text/plain"},
    ".txt": {"text/plain"},
    ".doc": {"application/msword", "application/octet-stream"},
}


class ZoteroSourceService:
    """Create sources without storing API credentials or pretending they are folders."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, payload: ZoteroSourceCreate) -> ZoteroLibrary:
        existing = await self._session.scalar(
            select(ZoteroLibrary).where(
                ZoteroLibrary.library_type == payload.library_type,
                ZoteroLibrary.library_id == payload.library_id,
            )
        )
        if existing is not None:
            raise ConflictError("Zotero library is already registered")
        root = f"zotero://{payload.library_type}/{payload.library_id}"
        source = KnowledgeSource(
            name=payload.name,
            source_type="zotero_library",
            root_path=root,
            normalized_root_path=root.casefold(),
            enabled=True,
            sync_status="idle",
        )
        self._session.add(source)
        await self._session.flush()
        library = ZoteroLibrary(
            knowledge_source_id=source.id,
            library_type=payload.library_type,
            library_id=payload.library_id,
        )
        self._session.add(library)
        await self._session.flush()
        return library

    async def delete(self, source_id: int) -> None:
        library = await self._session.scalar(
            select(ZoteroLibrary).where(ZoteroLibrary.knowledge_source_id == source_id)
        )
        if library is None:
            raise NotFoundError("Zotero source not found")
        source = await self._session.get(KnowledgeSource, source_id)
        if source is not None:
            # This only deletes database metadata; no remote item or attachment is touched.
            await self._session.delete(source)
        await self._session.flush()


class ZoteroSyncService:
    """Apply versioned remote metadata while retaining last-known active data on failure."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def sync(self, source_id: int, fetch_page, fetch_attachment=None) -> dict[str, int]:
        library = await self._session.scalar(
            select(ZoteroLibrary).where(ZoteroLibrary.knowledge_source_id == source_id)
        )
        if library is None:
            raise NotFoundError("Zotero source not found")
        try:
            result = fetch_page()
            page: ZoteroIncrementalResult = await result if inspect.isawaitable(result) else result
        except Exception:
            library.is_stale = True
            library.last_error_code = "zotero_sync_failed"
            await self._session.flush()
            raise
        metadata_only = 0
        attachments = 0
        for collection in page.collections:
            cached = await self._session.scalar(
                select(ZoteroCollection).where(
                    ZoteroCollection.zotero_library_id == library.id,
                    ZoteroCollection.collection_key == collection.key,
                )
            )
            if cached is None:
                cached = ZoteroCollection(
                    zotero_library_id=library.id,
                    collection_key=collection.key,
                    parent_key=collection.parent_key,
                    name=collection.name,
                    version=collection.version,
                    is_deleted=collection.is_deleted,
                )
                self._session.add(cached)
            else:
                cached.parent_key = collection.parent_key
                cached.name = collection.name
                cached.version = collection.version
                cached.is_deleted = collection.is_deleted
        for item in page.items:
            data = item.data
            is_deleted = bool(data.get("deleted", False))
            item_type = str(data.get("itemType", ""))
            is_attachment = item_type == "attachment"
            document = await self._session.scalar(
                select(Document).where(
                    Document.knowledge_source_id == source_id,
                    Document.zotero_item_key == item.key,
                )
            )
            title = str(data.get("title") or item.key)[:500]
            digest = sha256(f"{source_id}:{item.key}:{item.version}".encode()).hexdigest()
            if is_deleted:
                if document is not None:
                    # Keep the value within the shared document state machine;
                    # the structured error code carries the remote tombstone
                    # reason and keeps old content out of AI-available counts.
                    document.scan_state = "outdated"
                    document.parse_status = "failed"
                    document.index_status = "failed"
                    document.error_code = "zotero_tombstoned"
                    document.error_message = "Remote Zotero item was deleted"
                    document.paperqa_index_key = None
                    document.zotero_version = item.version
                continue
            if document is None:
                document = Document(
                    knowledge_source_id=source_id,
                    file_path=f"zotero/{item.key}",
                    normalized_file_path=f"zotero/{item.key}".casefold(),
                    file_hash=digest,
                    file_size=0,
                    modified_time=datetime.now(UTC),
                    modified_time_ns=0,
                    scan_state="pending",
                    parse_status="pending" if is_attachment else "succeeded",
                    index_status="pending",
                    parsed_title=title,
                    zotero_item_key=item.key,
                    zotero_parent_item_key=str(data.get("parentItem") or "") or None,
                    zotero_version=item.version,
                    metadata_only=not is_attachment,
                )
                self._session.add(document)
            else:
                document.zotero_version = item.version
                document.parsed_title = title
                document.metadata_only = not is_attachment
            if is_attachment:
                attachments += 1
                # Attachment bytes may be unavailable to the configured library
                # account.  Still create the normal durable pipeline command so
                # the task center can report a real failure/repair state instead
                # of presenting it as indexed metadata.
                if fetch_attachment is not None:
                    attachment = fetch_attachment(item.key)
                    attachment = (
                        await attachment if inspect.isawaitable(attachment) else attachment
                    )
                    await self._store_attachment(document, attachment)
                await self._session.flush()
                await DocumentTaskService(self._session).enqueue(document.id, "reparse")
            else:
                metadata_only += 1
        library.version_cursor = page.version or library.version_cursor
        library.last_synced_at = datetime.now(UTC)
        library.is_stale = False
        library.last_error_code = None
        await self._session.flush()
        return {"metadata_only": metadata_only, "attachments": attachments}

    async def _store_attachment(
        self, document: Document, attachment: ZoteroAttachment
    ) -> None:
        """Persist a verified official attachment as a managed asset once."""
        filename = self._safe_filename(attachment.filename)
        suffix = Path(filename).suffix.casefold()
        if suffix not in _ZOTERO_ATTACHMENT_TYPES:
            document.error_code = "unsupported_format"
            document.error_message = "Zotero attachment format is not supported"
            document.parse_status = "failed"
            return
        if attachment.media_type not in _ZOTERO_ATTACHMENT_TYPES[suffix]:
            document.error_code = "invalid_mime"
            document.error_message = "Zotero attachment media type does not match filename"
            document.parse_status = "failed"
            return
        if not attachment.content or len(attachment.content) > settings.MAX_LIBRARY_UPLOAD_BYTES:
            document.error_code = "attachment_too_large"
            document.error_message = "Zotero attachment is empty or exceeds the configured limit"
            document.parse_status = "failed"
            return
        if suffix == ".pdf" and not attachment.content.startswith(b"%PDF-"):
            document.error_code = "invalid_signature"
            document.error_message = "Zotero attachment content does not match PDF"
            document.parse_status = "failed"
            return
        digest = sha256(attachment.content).hexdigest()
        asset = await self._session.scalar(
            select(DocumentAsset).where(DocumentAsset.document_id == document.id)
        )
        if asset is not None and asset.sha256 == digest:
            return
        root = settings.UPLOAD_DIR.resolve()
        target = root / "library" / "zotero" / f"{uuid4().hex}{suffix}"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(attachment.content)
        document.file_path = target.relative_to(root).as_posix()
        document.normalized_file_path = document.file_path.casefold()
        document.file_hash = digest
        document.file_size = len(attachment.content)
        document.modified_time = datetime.now(UTC)
        document.modified_time_ns = 0
        document.error_code = None
        document.error_message = None
        if asset is None:
            self._session.add(
                DocumentAsset(
                    document_id=document.id,
                    asset_kind="zotero_attachment",
                    original_filename=filename,
                    stored_relative_path=document.file_path,
                    media_type=attachment.media_type,
                    byte_size=len(attachment.content),
                    sha256=digest,
                    processing_status="queued",
                )
            )
        else:
            asset.original_filename = filename
            asset.stored_relative_path = document.file_path
            asset.media_type = attachment.media_type
            asset.byte_size = len(attachment.content)
            asset.sha256 = digest
            asset.processing_status = "queued"

    @staticmethod
    def _safe_filename(value: str) -> str:
        if not value or Path(value).name != value or PureWindowsPath(value).name != value:
            return "attachment"
        return value[:255]
