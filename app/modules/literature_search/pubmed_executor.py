"""PubMed 检索执行器。

职责：把布尔检索式通过 ESearch 拿到 PMID 列表，再用 EFetch 拉取标准化记录，
收敛为带引用反幻觉验证标记的 CitationItem 列表。

反幻觉协议：verified 只表示"元数据来自 PubMed 真实 API 响应"。EFetch 返回的
记录本身即是真实数据，因此来自 fetch_records 的条目 verified=true；未返回的
PMID 条目不会被伪造或补全。verified_on 使用执行时刻的 UTC ISO 时间。
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.schemas import PubMedRecord
from app.modules.literature_search.schema import CitationItem

VERIFIED_BY_PUBMED = "pubmed"


class PubMedExecutor:
    """基于 PubMedClient 的检索执行与 verified 标记封装。"""

    def __init__(self, client: PubMedClient) -> None:
        self._client = client

    async def execute(self, query: str, *, retmax: int = 20) -> tuple[list[CitationItem], int]:
        """执行检索，返回 (条目列表, 命中总数)。

        ESearch 无命中时直接返回空列表；命中时用 EFetch 拉取记录。EFetch 可能
        因个别 PMID 已失效而少返回，此时不会为缺失条目补造占位数据。
        """
        search = await self._client.search(query, retmax=retmax)
        if not search.pmids:
            return [], search.total_count
        records = await self._client.fetch_records(search.pmids)
        verified_on = datetime.now(UTC).isoformat()
        items = [self._to_citation(record, verified_on) for record in records]
        return items, search.total_count

    @staticmethod
    def _to_citation(record: PubMedRecord, verified_on: str) -> CitationItem:
        """把 PubMedRecord 收敛为 CitationItem，并打上真实来源验证标记。

        has_abstract / publication_types 自 R2-WP05 起如实标注：摘要与文献
        类型字段直接来自 EFetch 响应，缺失时不补造、不推断，保证筛选
        "是否有摘要 / 文献类型"基于真实数据。
        """
        return CitationItem(
            pmid=record.pmid,
            doi=record.doi,
            title=record.title,
            authors=record.authors,
            journal=record.journal,
            year=record.year,
            verified=True,
            verified_by=VERIFIED_BY_PUBMED,
            verified_on=verified_on,
            has_abstract=bool(record.abstract),
            publication_types=record.publication_types,
            withdrawn=record.withdrawn,
        )
