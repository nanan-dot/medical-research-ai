"""只读 A0 查询与本地知识源授权；不暴露未完成的正文。"""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError, PermissionDeniedError
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.repository import DocumentAnchorRepository
from app.modules.document_anchor.schema import (
    AnchorManifestRead,
    AnchorRevisionRead,
    AnchorRevisionState,
    SourcePageQualityRead,
)
from app.modules.document_anchor.toolchain import (
    EXTRACTOR_VERSION,
    NORMALIZATION_VERSION,
    OPTIONS_HASH,
)
from app.modules.knowledge_source.model import KnowledgeSource

VISIBLE = {"ready", "review_required", "stale"}


class AnchorQueries:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._documents = DocumentRepository(session)
        self._anchors = DocumentAnchorRepository(session)

    async def authorized_document(
        self, document_id: int, *, fresh: bool = False
    ) -> Document:
        document = await self._documents.get(document_id)
        if document is None:
            raise NotFoundError("Document not found")
        if fresh:
            await self._session.refresh(document)
        source = await self._session.get(KnowledgeSource, document.knowledge_source_id)
        if fresh and source is not None:
            await self._session.refresh(source)
        if source is None or not source.enabled:
            raise PermissionDeniedError("Document source is unavailable")
        return document

    async def manifest(self, document_id: int) -> AnchorManifestRead:
        document = await self.authorized_document(document_id)
        revision = await self._anchors.latest_visible(document_id)
        if revision and (
            revision.file_hash != document.file_hash
            or revision.options_hash != OPTIONS_HASH
            or revision.extractor_version != EXTRACTOR_VERSION
            or revision.normalization_version != NORMALIZATION_VERSION
        ):
            revision = None
        return AnchorManifestRead(
            document_id=document_id,
            revision=self.revision_read(revision) if revision else None,
        )

    async def get_revision(self, revision_id: int) -> AnchorRevisionRead:
        revision = await self._anchors.get_revision(revision_id)
        if revision is None:
            raise NotFoundError("Anchor revision not found")
        await self.authorized_document(revision.document_id)
        return self.revision_read(revision)

    async def page_quality(
        self, document_id: int, revision_id: int, page_number: int
    ) -> SourcePageQualityRead:
        await self.authorized_document(document_id)
        revision = await self._anchors.get_for_document(document_id, revision_id)
        if revision is None or revision.state not in VISIBLE:
            raise NotFoundError("Completed anchor revision not found for document")
        page = await self._anchors.page_quality(revision.id, page_number)
        if page is None:
            raise NotFoundError("Anchor page not found")
        return SourcePageQualityRead(
            revision_id=revision.id,
            document_id=document_id,
            page_number=page.page_number,
            text_item_count=page.text_item_count,
            quality_flags=json.loads(page.quality_flags_json),
            quality_metrics=json.loads(page.quality_metrics_json),
        )

    async def text_items(
        self,
        document_id: int,
        revision_id: int,
        page_number: int,
        start: int = 0,
        limit: int = 200,
    ) -> list[DocumentSourceTextItem]:
        """Internal locating/A1 query, scoped and capped; no whole-document HTTP dump."""
        if start < 0 or not 1 <= limit <= 200:
            raise ValueError("TextItem query exceeds bounded range")
        await self.page_quality(document_id, revision_id, page_number)
        page = await self._anchors.page_quality(revision_id, page_number)
        if page is None:
            raise NotFoundError("Anchor page not found")
        return await self._anchors.text_items(page.id, start, limit)

    @staticmethod
    def revision_read(
        revision: DocumentAnchorRevision, task_id: int | None = None
    ) -> AnchorRevisionRead:
        return AnchorRevisionRead(
            id=revision.id,
            document_id=revision.document_id,
            file_hash=revision.file_hash,
            state=AnchorRevisionState(revision.state),
            task_id=task_id,
            pdfjs_version=revision.pdfjs_version,
            normalization_version=revision.normalization_version,
            extractor_version=revision.extractor_version,
            request_fingerprint=revision.request_fingerprint,
            extraction_fingerprint=revision.extraction_fingerprint,
            options_hash=revision.options_hash,
            quality_summary=json.loads(revision.quality_summary_json),
            error_code=revision.error_code,
            error_message=revision.error_message,
            created_at=revision.created_at,
            finished_at=revision.finished_at,
        )
