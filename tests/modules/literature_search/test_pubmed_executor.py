"""PubMedExecutor 单元测试。

使用替身客户端，不访问真实网络。重点验证反幻觉协议：只有 fetch_records
真实返回的记录才标 verified=true；未命中的 PMID 不会被补造。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.integrations.pubmed.schemas import PubMedRecord, PubMedSearchResult
from app.modules.literature_search.pubmed_executor import (
    VERIFIED_BY_PUBMED,
    PubMedExecutor,
)


@dataclass
class FakePubMedClient:
    """替身客户端：可编程返回搜索与记录结果。"""

    search_result: PubMedSearchResult = field(default_factory=PubMedSearchResult)
    records: list[PubMedRecord] = field(default_factory=list)
    search_calls: int = 0
    last_search_retmax: int | None = None

    async def search(self, query: str, *, retmax: int = 20) -> PubMedSearchResult:
        self.search_calls += 1
        self.last_search_retmax = retmax
        return self.search_result

    async def fetch_records(self, pmids: list[str]) -> list[PubMedRecord]:
        return self.records


def _record(pmid: str = "39000401") -> PubMedRecord:
    return PubMedRecord(
        pmid=pmid,
        doi=f"10.1016/j.example.{pmid}",
        title="A real PubMed record",
        authors=["Kim J"],
        journal="Nature Medicine",
        year=2024,
        pmcid="PMC1234567",
    )


async def test_execute_marks_records_verified_from_pubmed():
    client = FakePubMedClient(
        search_result=PubMedSearchResult(pmids=["39000401"], total_count=42),
        records=[_record()],
    )
    items, total = await PubMedExecutor(client).execute("query", retmax=20)

    assert total == 42
    assert len(items) == 1
    item = items[0]
    assert item.verified is True
    assert item.verified_by == VERIFIED_BY_PUBMED
    assert item.verified_on is not None
    assert item.pmid == "39000401"
    assert item.pmcid == "PMC1234567"


def test_legacy_citation_snapshot_without_pmcid_remains_readable():
    from app.modules.literature_search.schema import CitationItem

    citation = CitationItem.model_validate({"pmid": "123", "title": "Legacy"})

    assert citation.pmcid is None


async def test_execute_empty_search_returns_no_items():
    client = FakePubMedClient(
        search_result=PubMedSearchResult(pmids=[], total_count=0),
    )
    items, total = await PubMedExecutor(client).execute("query")

    assert items == []
    assert total == 0
    assert client.search_calls == 1


async def test_execute_does_not_fabricate_missing_records():
    # ESearch 返回 2 个 PMID，但 EFetch 只返回 1 条：缺失条目不补造。
    client = FakePubMedClient(
        search_result=PubMedSearchResult(pmids=["39000401", "99999999"], total_count=2),
        records=[_record()],
    )
    items, _ = await PubMedExecutor(client).execute("query")

    assert len(items) == 1
    assert items[0].pmid == "39000401"


async def test_execute_uses_a_small_buffer_but_caps_persisted_items():
    client = FakePubMedClient(
        search_result=PubMedSearchResult(
            pmids=[str(index) for index in range(525)], total_count=1000
        ),
        records=[_record(str(index)) for index in range(525)],
    )

    items, total = await PubMedExecutor(client).execute("query", retmax=500)

    assert total == 1000
    assert len(items) == 500
    assert client.last_search_retmax == 525
