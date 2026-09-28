"""用既有可信数据源补全论文元数据。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.integrations.pubmed.schemas import PubMedRecord, PubMedSearchResult
from app.modules.document.matcher import normalize_doi
from app.modules.document.service import sanitize_error_message
from app.modules.library_item.model import LibraryItem
from app.modules.literature_search.journal_metric_matching import match_journal_metric
from app.modules.literature_search.journal_metric_normalization import (
    normalize_journal_name,
)
from app.modules.literature_search.journal_metric_query import summarize_metrics
from app.modules.literature_search.journal_metric_repository import (
    JournalMetricRepository,
)
from app.modules.literature_search.schema import CitationItem


class MetadataClient(Protocol):
    async def search(self, query: str, *, retmax: int = 20) -> PubMedSearchResult: ...

    async def fetch_records(self, pmids: list[str]) -> list[PubMedRecord]: ...

    async def aclose(self) -> None: ...


class PaperMetadataService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        client_factory: Callable[[], MetadataClient] | None = None,
    ) -> None:
        self.session = session
        self.client_factory = client_factory or PubMedClient.from_settings

    async def enrich(self, item: LibraryItem) -> LibraryItem:
        """只填充空字段；标识冲突和上游故障会持久化为可观察状态。"""
        await self.session.execute(
            update(LibraryItem)
            .where(LibraryItem.id == item.id)
            .values(
                metadata_status="running",
                metadata_retry_count=LibraryItem.metadata_retry_count + 1,
                metadata_last_attempt_at=datetime.now(UTC),
                metadata_error_code=None,
                metadata_error_message=None,
            )
        )
        # 原子自增后刷新同一 ORM 实例，避免两个独立会话把重试次数都写回 1。
        await self.session.refresh(item)

        client = self.client_factory()
        try:
            record = await self._fetch_record(client, item)
            if record is None:
                item.metadata_status = "not_found"
                item.metadata_source = "pubmed"
                item.metadata_error_code = "metadata_not_found"
                item.metadata_error_message = "PubMed 未返回匹配论文"
                await self.session.flush()
                return item
            if self._has_identity_conflict(item, record):
                item.metadata_status = "failed"
                item.metadata_source = "pubmed"
                item.metadata_error_code = "identifier_conflict"
                item.metadata_error_message = "可信元数据与现有 DOI/PMID 冲突"
                await self.session.flush()
                return item
            if await self._identity_owned_by_another_item(item, record):
                item.metadata_status = "failed"
                item.metadata_source = "pubmed"
                item.metadata_error_code = "identifier_conflict"
                item.metadata_error_message = "补全后的论文标识已被其他记录占用"
                await self.session.flush()
                return item
            try:
                # 预查询只能改善报错信息，无法消除两个会话同时补全的窗口；
                # 仍以数据库唯一键为最终裁判，并把竞争收敛为可恢复业务状态。
                async with self.session.begin_nested():
                    self._fill_blank_fields(item, record)
                    await self._fill_journal_metric(item, record)
                    item.metadata_status = "succeeded"
                    item.metadata_source = "pubmed"
                    item.metadata_error_code = None
                    item.metadata_error_message = None
                    item.updated_at = datetime.now(UTC)
                    await self.session.flush()
            except IntegrityError:
                await self.session.refresh(item)
                item.metadata_status = "failed"
                item.metadata_source = "pubmed"
                item.metadata_error_code = "identifier_conflict"
                item.metadata_error_message = "补全后的论文标识已被其他记录占用"
                await self.session.flush()
            return item
        except PubMedError as exc:
            item.metadata_status = "failed"
            item.metadata_source = "pubmed"
            item.metadata_error_code = exc.code
            item.metadata_error_message = sanitize_error_message(exc.message)
            await self.session.flush()
            return item
        finally:
            await client.aclose()

    async def _fetch_record(
        self, client: MetadataClient, item: LibraryItem
    ) -> PubMedRecord | None:
        if item.pmid:
            records = await client.fetch_records([item.pmid])
            return records[0] if records else None
        if not item.doi:
            return None
        found = await client.search(f'"{item.doi}"[AID]', retmax=5)
        if not found.pmids:
            return None
        records = await client.fetch_records(found.pmids)
        normalized = normalize_doi(item.doi)
        return next(
            (record for record in records if normalize_doi(record.doi) == normalized),
            None,
        )

    @staticmethod
    def _has_identity_conflict(item: LibraryItem, record: PubMedRecord) -> bool:
        return bool(
            (item.pmid and item.pmid != record.pmid)
            or (
                item.doi
                and record.doi
                and normalize_doi(item.doi) != normalize_doi(record.doi)
            )
        )

    async def _identity_owned_by_another_item(
        self, item: LibraryItem, record: PubMedRecord
    ) -> bool:
        clauses = [LibraryItem.pmid == record.pmid]
        normalized_doi = normalize_doi(record.doi)
        if normalized_doi:
            clauses.append(LibraryItem.doi == normalized_doi)
        statement = select(LibraryItem.id).where(
            LibraryItem.id != item.id,
            or_(*clauses),
        )
        return (await self.session.scalar(statement.limit(1))) is not None

    @staticmethod
    def _fill_blank_fields(item: LibraryItem, record: PubMedRecord) -> None:
        item.pmid = item.pmid or record.pmid
        item.pmcid = item.pmcid or record.pmcid
        item.doi = item.doi or normalize_doi(record.doi)
        item.title = item.title or record.title
        item.authors = item.authors or "; ".join(record.authors) or None
        item.journal = item.journal or record.journal
        item.year = item.year or record.year
        item.paper_type = item.paper_type or _paper_type(record.publication_types)

    async def _fill_journal_metric(
        self, item: LibraryItem, record: PubMedRecord
    ) -> None:
        repository = JournalMetricRepository(self.session)
        if not await repository.has_active_batches():
            return
        citation = CitationItem(
            pmid=record.pmid,
            doi=record.doi,
            title=record.title,
            authors=record.authors,
            journal=record.journal,
            issn=record.issn,
            eissn=record.eissn,
            issn_l=record.issn_l,
        )
        issns = {value for value in (record.issn_l, record.issn, record.eissn) if value}
        normalized_name = normalize_journal_name(record.journal)
        candidates = await repository.candidates(
            issns, {normalized_name} if normalized_name else set()
        )
        match = match_journal_metric(citation, candidates)
        if match.status != "matched" or not match.journal_key or not match.method:
            return
        matched_rows = [
            row for row in candidates if row.journal_key == match.journal_key
        ]
        summary = summarize_metrics(matched_rows, match.method)
        if summary.latest and summary.latest.jcr.best_quartile:
            provenance = next(
                (
                    row
                    for row in sorted(
                        matched_rows, key=lambda value: value.metric_year or 0, reverse=True
                    )
                    if row.jcr_best_quartile
                ),
                None,
            )
            item.journal_quartile = (
                item.journal_quartile or summary.latest.jcr.best_quartile
            )
            item.journal_quartile_source = (
                item.journal_quartile_source
                or (
                    f"journal_metric:{provenance.provider}:{match.method}"
                    if provenance
                    else f"journal_metric:{match.method}"
                )
            )
            item.journal_quartile_year = (
                item.journal_quartile_year or summary.latest.jcr.year
            )


def _paper_type(publication_types: list[str]) -> str | None:
    normalized = {value.casefold() for value in publication_types}
    rules = (
        ("randomized controlled trial", "RCT"),
        ("meta-analysis", "Meta-analysis"),
        ("systematic review", "Systematic Review"),
        ("practice guideline", "Guideline"),
        ("guideline", "Guideline"),
    )
    return next((label for source, label in rules if source in normalized), None)
