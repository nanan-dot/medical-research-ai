"""PubMedClient 真实网络集成测试（显式门控）。

运行方式：
    RUN_PUBMED_LIVE_TEST=1 pytest tests/integrations/test_pubmed_live.py -v

未设置该环境变量时全部跳过，避免 CI/离线环境意外访问外网。
"""

import os

import pytest

from app.integrations.pubmed import PubMedClient

pytestmark = pytest.mark.integration

# 用确定存在的经典文献做核对锚点（PMID 由 ESearch 结果得出，不手动编造）。
SEARCH_QUERY = '("neural networks"[Title/Abstract]) AND "mammography"[Title/Abstract]'


def _skip_unless_enabled() -> None:
    if os.getenv("RUN_PUBMED_LIVE_TEST") != "1":
        pytest.skip("set RUN_PUBMED_LIVE_TEST=1 to run live PubMed integration tests")


@pytest.mark.asyncio
async def test_live_search_returns_pmids_and_counts():
    _skip_unless_enabled()
    async with PubMedClient() as client:
        result = await client.search(SEARCH_QUERY, retmax=3)

    assert result.pmids, "expected at least one PMID for the live query"
    assert len(result.pmids) <= 3
    assert result.total_count >= len(result.pmids)
    assert all(pmid.isdigit() for pmid in result.pmids)


@pytest.mark.asyncio
async def test_live_empty_query_returns_no_pmids():
    _skip_unless_enabled()
    async with PubMedClient() as client:
        result = await client.search('"zzzznotamedicaltermxyz"', retmax=5)

    assert result.pmids == []
    assert result.total_count == 0


@pytest.mark.asyncio
async def test_live_efetch_returns_normalized_records():
    _skip_unless_enabled()
    async with PubMedClient() as client:
        result = await client.search(SEARCH_QUERY, retmax=2)
        if not result.pmids:
            pytest.skip("live query returned no pmids")
        records = await client.fetch_records(result.pmids)

    assert records
    for record in records:
        assert record.pmid.isdigit()
        assert record.title, "title should be present for a real record"
        assert isinstance(record.year, int) or record.year is None
        assert isinstance(record.authors, list)
        # 反幻觉：标题或 DOI 必须来自响应，而不是空值。
        assert record.title or record.doi


@pytest.mark.asyncio
async def test_live_esummary_returns_metadata():
    _skip_unless_enabled()
    async with PubMedClient() as client:
        result = await client.search(SEARCH_QUERY, retmax=1)
        if not result.pmids:
            pytest.skip("live query returned no pmids")
        summary = await client.fetch_summary(result.pmids)

    assert result.pmids[0] in summary
    assert summary[result.pmids[0]]["title"]
