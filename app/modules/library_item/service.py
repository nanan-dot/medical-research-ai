"""library_item — 保存检索元数据到本地知识库的编排服务。

fulltext-retrieval 融合点：保存只记录全文状态（基于可验证信号），绝不自动
下载或绕过付费墙；状态与理由一并返回，前端可解释。
"""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.document.matcher import find_exact_document_match, normalize_doi
from app.modules.document.repository import DocumentRepository
from app.modules.library_item.model import LibraryItem
from app.modules.library_item.repository import LibraryItemRepository
from app.modules.library_item.schema import (
    FulltextStatus,
    LibraryItemPage,
    LibraryItemRead,
)
from app.modules.literature_search.model import LiteratureSearchResult
from app.modules.literature_search.schema import CitationItem

_METADATA_REASON = "No local PDF or verified open-access signal in the saved result"
logger = logging.getLogger(__name__)


class LibraryItemService:
    def __init__(self, session: AsyncSession):
        self.repo = LibraryItemRepository(session)
        self.document_repo = DocumentRepository(session)
        self.session = session

    async def save_search_result(self, result_id: int, pmid: str) -> LibraryItemRead:
        """把检索结果中的一条文献保存为正式收藏。

        幂等：同一 (pmid 或 doi) 已存在时返回已有记录，不重复创建。
        自动匹配：精确 PMID/DOI 命中本地文档则标 local_pdf_available；
        否则 metadata_only（不自动下载、不伪造 OA 信号）。
        """
        result = await self.session.get(LiteratureSearchResult, result_id)
        if result is None:
            raise NotFoundError(f"LiteratureSearchResult not found: {result_id}")
        citation = next(
            (
                CitationItem.model_validate(raw)
                for raw in json.loads(result.items_json)
                if raw.get("pmid") == pmid
            ),
            None,
        )
        if citation is None:
            raise NotFoundError(f"CitationItem not found: {pmid}")
        doi = normalize_doi(citation.doi)
        existing = await self.repo.find_by_identifier(citation.pmid, doi)
        if existing is not None:
            if existing.pmcid is None and citation.pmcid is not None:
                existing.pmcid = citation.pmcid
                existing.updated_at = datetime.now(UTC)
                existing = await self.repo.save(existing)
            elif (
                existing.pmcid is not None
                and citation.pmcid is not None
                and existing.pmcid != citation.pmcid
            ):
                logger.warning(
                    "PMCID conflict kept existing value library_item_id=%d pmid=%s",
                    existing.id,
                    citation.pmid,
                )
                raise ConflictError(
                    "Saved LibraryItem PMCID conflicts with PubMed snapshot"
                )
            return LibraryItemRead.model_validate(existing)
        match = find_exact_document_match(
            await self.document_repo.list_all(), pmid=citation.pmid, doi=doi
        )
        if match is not None:
            status = FulltextStatus.LOCAL_PDF_AVAILABLE
            reason = "Exact PMID/DOI match in local document"
            document_id = match.id
        else:
            status = FulltextStatus.METADATA_ONLY
            reason = _METADATA_REASON
            document_id = None
        item = LibraryItem(
            pmid=citation.pmid,
            pmcid=citation.pmcid,
            doi=doi,
            title=citation.title,
            journal=citation.journal,
            year=citation.year,
            source_search_id=result_id,
            document_id=document_id,
            fulltext_status=status.value,
            fulltext_status_reason=reason,
        )
        return LibraryItemRead.model_validate(await self.repo.create(item))

    async def link_local_pdf(
        self, item_id: int, document_id: int | None
    ) -> LibraryItemRead:
        """手动绑定/解绑本地 PDF；document_id=None 表示解绑（元数据保留）。"""
        item = await self._get(item_id)
        if document_id is None:
            item.document_id = None
            item.fulltext_status = FulltextStatus.METADATA_ONLY.value
            item.fulltext_status_reason = "Local PDF link removed; metadata retained"
        else:
            document = await self.document_repo.get(document_id)
            if document is None:
                raise NotFoundError(f"Document not found: {document_id}")
            item.document_id = document.id
            item.fulltext_status = FulltextStatus.LOCAL_PDF_AVAILABLE.value
            item.fulltext_status_reason = "Local PDF explicitly linked by user"
        item.updated_at = datetime.now(UTC)
        return LibraryItemRead.model_validate(await self.repo.save(item))

    async def list(
        self, offset: int, limit: int, status: FulltextStatus | None
    ) -> LibraryItemPage:
        status_value = status.value if status else None
        items = [
            LibraryItemRead.model_validate(item)
            for item in await self.repo.list_items(offset, limit, status_value)
        ]
        total = await self.repo.count(status_value)
        return LibraryItemPage(items=items, total=total, offset=offset, limit=limit)

    async def _get(self, item_id: int) -> LibraryItem:
        item = await self.repo.get(item_id)
        if item is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        return item
