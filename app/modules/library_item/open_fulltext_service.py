"""Orchestrate legal PMC verification, controlled download, and local linkage."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.common.path_utils import normalized_path_key
from app.modules.document.matcher import normalize_doi
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document_upload.model import DocumentAsset
from app.modules.document_upload.repository import DocumentAssetRepository
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.schema import (
    KnowledgeSourceSyncStatus,
    KnowledgeSourceType,
)
from app.modules.library_item.model import LibraryItem
from app.modules.library_item.official_pmc_client import (
    OfficialPmcClient,
    OfficialPmcError,
    OfficialPmcGateway,
    VerifiedPmcFulltext,
)
from app.modules.library_item.open_fulltext_model import OpenFulltextAcquisition
from app.modules.library_item.open_fulltext_repository import (
    OpenFulltextAcquisitionRepository,
)
from app.modules.library_item.open_fulltext_schema import (
    OpenFulltextAcquisitionRead,
    OpenFulltextResult,
    OpenFulltextStatus,
)
from app.modules.library_item.open_fulltext_storage import (
    OpenFulltextStorage,
    StoredOpenFulltextPdf,
)
from app.modules.library_item.repository import LibraryItemRepository
from app.modules.library_item.schema import FulltextStatus, LibraryItemRead

_PMC_SOURCE_NAME = "PMC 官方开放全文"


class OpenFulltextService:
    """A success means every legal and file-integrity gate has completed.

    本服务故意不把“PMC 收录”或“有开放链接”当作成功：只有官方 OAI 身份、许可、
    OA Web Service PDF、流式文件校验和数据库关联全部成功后，才更新收藏项为本地全文。
    """

    def __init__(
        self,
        session: AsyncSession,
        *,
        gateway: OfficialPmcGateway | None = None,
        storage: OpenFulltextStorage | None = None,
    ) -> None:
        self._session = session
        self._items = LibraryItemRepository(session)
        self._acquisitions = OpenFulltextAcquisitionRepository(session)
        self._documents = DocumentRepository(session)
        self._assets = DocumentAssetRepository(session)
        self._sources = KnowledgeSourceRepository(session)
        self._gateway = gateway
        self._storage = storage or OpenFulltextStorage()

    async def acquire(self, item_id: int, pmcid: str) -> OpenFulltextResult:
        item = await self._get_item(item_id)
        existing = await self._acquisitions.get_by_library_item(item_id)
        if (
            existing is not None
            and existing.status == OpenFulltextStatus.SUCCEEDED.value
            and existing.pmcid == pmcid
            and existing.document_id is not None
        ):
            return self._result(item, existing)

        gateway = self._gateway or OfficialPmcClient()
        owns_gateway = self._gateway is None
        try:
            verified = await gateway.fetch_verified_fulltext(pmcid)
            self._verify_identity(item, verified)
            stored = await self._storage.store(gateway, verified.pmcid, verified.pdf_url)
        except OfficialPmcError as exc:
            return await self._persist_failure(item, pmcid, exc)
        finally:
            if owns_gateway:
                await gateway.aclose()

        try:
            return await self._persist_success(item, verified, stored)
        except Exception:
            await self._session.rollback()
            await self._remove_stored_file(stored.absolute_path)
            raise

    async def _persist_success(
        self,
        item: LibraryItem,
        verified: VerifiedPmcFulltext,
        stored: StoredOpenFulltextPdf,
    ) -> OpenFulltextResult:
        source = await self._get_or_create_source(stored.absolute_path.parent.parent)
        document = Document(
            knowledge_source_id=source.id,
            file_path=str(stored.absolute_path),
            normalized_file_path=os.path.normcase(os.path.normpath(stored.relative_path)),
            file_hash=stored.sha256,
            file_size=stored.byte_size,
            modified_time=stored.modified_time,
            modified_time_ns=stored.modified_time_ns,
            scan_state="pending",
            parse_status="pending",
            index_status="pending",
        )
        await self._documents.create(document)
        asset = DocumentAsset(
            document=document,
            asset_kind="pmc_open_access",
            original_filename=f"{verified.pmcid}.pdf",
            stored_relative_path=stored.relative_path,
            media_type="application/pdf",
            byte_size=stored.byte_size,
            sha256=stored.sha256,
            processing_status="pending_parse",
            source_url=verified.pdf_url,
            license=verified.license,
            retrieved_at=datetime.now(UTC),
        )
        await self._assets.create(asset)
        acquisition = OpenFulltextAcquisition(
            library_item_id=item.id,
            pmcid=verified.pmcid,
            status=OpenFulltextStatus.SUCCEEDED.value,
        )
        acquisition.document_id = document.id
        acquisition.pmcid = verified.pmcid
        acquisition.status = OpenFulltextStatus.SUCCEEDED.value
        acquisition.source_url = verified.oai_record_url
        acquisition.license = verified.license
        acquisition.file_format = "pdf"
        acquisition.file_sha256 = stored.sha256
        acquisition.error_code = None
        acquisition.error_message = None
        acquisition.attempted_at = datetime.now(UTC)
        acquisition.retrieved_at = datetime.now(UTC)
        self._session.add(acquisition)
        item.pmcid = verified.pmcid
        item.document_id = document.id
        item.fulltext_status = FulltextStatus.LOCAL_PDF_AVAILABLE.value
        item.fulltext_status_reason = (
            "Official PMC OAI identity and license verified; official OA PDF retrieved"
        )
        item.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(item)
        await self._session.refresh(acquisition)
        return self._result(item, acquisition)

    async def _persist_failure(
        self, item: LibraryItem, pmcid: str, error: OfficialPmcError
    ) -> OpenFulltextResult:
        acquisition = OpenFulltextAcquisition(
            library_item_id=item.id,
            pmcid=pmcid,
            status=error.code,
        )
        acquisition.document_id = None
        acquisition.pmcid = pmcid
        acquisition.status = _status_for_error(error.code).value
        acquisition.source_url = None
        acquisition.license = None
        acquisition.file_format = None
        acquisition.file_sha256 = None
        acquisition.error_code = error.code
        acquisition.error_message = error.message
        acquisition.attempted_at = datetime.now(UTC)
        acquisition.retrieved_at = None
        self._session.add(acquisition)
        if item.document_id is None:
            item.fulltext_status = FulltextStatus.UNAVAILABLE.value
            item.fulltext_status_reason = error.message
        else:
            item.fulltext_status_reason = (
                "A new PMC retrieval attempt failed; existing local document was preserved"
            )
        item.updated_at = datetime.now(UTC)
        await self._session.commit()
        await self._session.refresh(item)
        await self._session.refresh(acquisition)
        return self._result(item, acquisition)

    async def _get_or_create_source(self, root: Path) -> KnowledgeSource:
        normalized_root = normalized_path_key(root)
        source = await self._sources.get_by_normalized_path(normalized_root)
        if source is not None:
            return source
        source = KnowledgeSource(
            name=_PMC_SOURCE_NAME,
            source_type=KnowledgeSourceType.TEMPORARY_IMPORT.value,
            root_path=str(root),
            normalized_root_path=normalized_root,
            sync_status=KnowledgeSourceSyncStatus.IDLE.value,
        )
        return await self._sources.create(source)

    async def _get_item(self, item_id: int) -> LibraryItem:
        item = await self._items.get(item_id)
        if item is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        return item

    async def list_attempts(self, item_id: int) -> list[OpenFulltextAcquisitionRead]:
        await self._get_item(item_id)
        attempts = await self._acquisitions.list_by_library_item(item_id)
        return [OpenFulltextAcquisitionRead.model_validate(attempt) for attempt in attempts]

    @staticmethod
    def _verify_identity(item: LibraryItem, verified: VerifiedPmcFulltext) -> None:
        pmid_matches = verified.pmid is not None and verified.pmid == item.pmid
        doi_matches = (
            item.doi is not None
            and verified.doi is not None
            and normalize_doi(verified.doi) == normalize_doi(item.doi)
        )
        if not pmid_matches and not doi_matches:
            raise OfficialPmcError(
                "identity_mismatch",
                "PMC 官方记录的 PMID/DOI 与当前收藏条目不匹配，未下载全文",
            )

    @staticmethod
    def _result(
        item: LibraryItem, acquisition: OpenFulltextAcquisition
    ) -> OpenFulltextResult:
        return OpenFulltextResult(
            item=LibraryItemRead.model_validate(item),
            acquisition=OpenFulltextAcquisitionRead.model_validate(acquisition),
        )

    @staticmethod
    async def _remove_stored_file(path: Path) -> None:
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError:
            # 数据库异常的主错误更有诊断价值；清理失败不应遮蔽它。
            pass


def _status_for_error(error_code: str) -> OpenFulltextStatus:
    try:
        return OpenFulltextStatus(error_code)
    except ValueError:
        return OpenFulltextStatus.NETWORK_ERROR
