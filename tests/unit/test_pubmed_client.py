"""PubMedClient 单元测试。

全部使用 Mock httpx.AsyncClient / 本地注入，不访问真实网络。
覆盖任务要求：搜索ID、空结果、元数据、缺摘要、网络超时、429、非法XML、缓存命中、
作者复杂格式、年份缺失、撤回记录。
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from app.integrations.pubmed import PubMedClient
from app.integrations.pubmed.cache import TTLCache
from app.integrations.pubmed.client import _normalize_query_term
from app.integrations.pubmed.exceptions import (
    PubMedConfigurationError,
    PubMedConnectionError,
    PubMedRateLimitError,
    PubMedResponseError,
    PubMedTimeoutError,
)
from app.integrations.pubmed.rate_limit import RateLimiter

# ---------------------------------------------------------------------------
# 辅助构造
# ---------------------------------------------------------------------------


class FakeHTTPClient:
    """可编程的 httpx 客户端替身，按 endpoint+param 返回脚本化的响应。"""

    def __init__(self, responses: dict[str, Any], *, status_code: int = 200) -> None:
        # key: (endpoint, sorted params string) -> response 或异常
        self.responses = responses
        self.status_code = status_code
        self.requests: list[dict[str, str]] = []
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def get(self, url: str, params: dict[str, str]) -> httpx.Response:
        self.calls.append((url, params))
        self.requests.append(params)
        endpoint = url.rsplit("/", 1)[-1]
        # 优先按请求参数精确匹配，其次按 endpoint 兜底。
        key = f"{endpoint}|{sorted(params.items())}"
        scripted = self.responses.get(key)
        if scripted is None:
            scripted = self.responses.get(endpoint)
        if scripted is None:
            return httpx.Response(self.status_code, text="")
        if isinstance(scripted, Exception):
            raise scripted
        text = scripted if isinstance(scripted, str) else self._dump_json(scripted)
        return httpx.Response(
            self.status_code, text=text, request=httpx.Request("GET", url)
        )

    @staticmethod
    def _dump_json(payload: dict[str, Any]) -> str:
        return json.dumps(payload)


class InstantRateLimiter:
    """测试用：不实际等待的限流器，避免单测引入真实延迟。"""

    async def wait(self) -> None:
        return None


def fast_backoff(client: PubMedClient) -> PubMedClient:
    """把退避睡眠替换为 no-op，避免重试测试引入真实延迟。"""

    async def _noop(seconds: float) -> None:
        return None

    client._sleep_limited = _noop  # type: ignore[method-assign]
    return client


def make_client(responses: dict[str, Any], *, status_code: int = 200) -> PubMedClient:
    http = FakeHTTPClient(responses, status_code=status_code)
    return PubMedClient(
        http_client=http,  # type: ignore[arg-type]
        rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        cache=TTLCache(),
    )


def esearch_payload(pmids: list[str], count: int | None = None) -> dict[str, Any]:
    return {
        "esearchresult": {
            "count": str(count if count is not None else len(pmids)),
            "idlist": pmids,
        }
    }


def esummary_payload(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"result": {"uids": list(entries), **entries}}


# 标准 EFetch XML（无命名空间，NCBI efetch 默认格式）。
SAMPLE_EFETCH = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>38000001</PMID>
      <Article>
        <ArticleTitle>Robust meta-analysis of diagnostic accuracy</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">A diagnostic study.</AbstractText>
          <AbstractText Label="RESULTS">Found a high accuracy.</AbstractText>
        </Abstract>
        <Journal>
          <JournalIssue>
            <PubDate><Year>2024</Year><Month>Jan</Month></PubDate>
          </JournalIssue>
          <Title>Radiology</Title>
        </Journal>
        <AuthorList>
          <Author><LastName>Kim</LastName><ForeName>Jane</ForeName><Initials>JK</Initials></Author>
          <Author><LastName>Lee</LastName><ForeName>Min</ForeName><Initials>ML</Initials></Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
          <PublicationType>Meta-Analysis</PublicationType>
        </PublicationTypeList>
      </Article>
      <ArticleIdList>
        <ArticleId IdType="pubmed">38000001</ArticleId>
        <ArticleId IdType="doi">10.1148/radiol.202412345</ArticleId>
        <ArticleId IdType="pmc">PMC1234567</ArticleId>
      </ArticleIdList>
    </MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>
"""


# ---------------------------------------------------------------------------
# ESearch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_returns_real_pmids():
    client = make_client(
        {"esearch.fcgi": esearch_payload(["12345678", "87654321"], count=42)}
    )

    result = await client.search("diabetic retinopathy", retmax=2)

    assert result.pmids == ["12345678", "87654321"]
    assert result.total_count == 42


@pytest.mark.asyncio
async def test_search_empty_result_returns_empty_pmids():
    client = make_client({"esearch.fcgi": esearch_payload([], count=0)})

    result = await client.search("no such medical term", retmax=10)

    assert result.pmids == []
    assert result.total_count == 0


@pytest.mark.asyncio
async def test_search_blank_query_is_rejected():
    client = make_client({})
    with pytest.raises(PubMedConfigurationError, match="non-empty"):
        await client.search("   ")


@pytest.mark.asyncio
async def test_search_passes_email_and_tool_parameters():
    http = FakeHTTPClient({"esearch.fcgi": esearch_payload(["123"]), "tool": "x"})
    client = PubMedClient(
        http_client=http,  # type: ignore[arg-type]
        rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
    )
    client.config.email = "researcher@example.com"

    await client.search("diabetes", retmax=5)

    sent = http.requests[-1]
    assert sent["email"] == "researcher@example.com"
    assert sent["tool"].startswith("med-research")


@pytest.mark.asyncio
async def test_esearch_response_structure_change_is_tolerated():
    # 旧版响应把 esearchresult 放在顶层，idlist 可能是字符串。
    client = make_client({"esearch.fcgi": {"idlist": "999", "count": "1"}})

    result = await client.search("rare disease", retmax=3)

    assert result.pmids == ["999"]
    assert result.total_count == 1


# ---------------------------------------------------------------------------
# ESummary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_summary_returns_normalized_metadata():
    client = make_client(
        {
            "esummary.fcgi": esummary_payload(
                {
                    "123": {
                        "title": "A study",
                        "pubdate": "2023",
                        "source": "J Med",
                        "authors": [{"name": "John Smith"}],
                        "articleids": [{"idtype": "doi", "value": "10.1/abc"}],
                        "pubtype": ["Journal Article"],
                    }
                }
            )
        }
    )

    result = await client.fetch_summary(["123"])

    assert result["123"]["title"] == "A study"
    assert result["123"]["year"] == 2023
    assert result["123"]["journal"] == "J Med"
    assert result["123"]["authors"] == ["John Smith"]
    assert result["123"]["doi"] == "10.1/abc"


@pytest.mark.asyncio
async def test_fetch_summary_empty_pmids_returns_empty():
    client = make_client({})
    assert await client.fetch_summary([]) == {}


@pytest.mark.asyncio
async def test_esummary_missing_result_raises_response_error():
    client = make_client({"esummary.fcgi": {"unexpected": True}})
    with pytest.raises(PubMedResponseError, match="missing 'result'"):
        await client.fetch_summary(["1"])


# ---------------------------------------------------------------------------
# EFetch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fetch_records_parses_full_record():
    client = make_client({"efetch.fcgi": SAMPLE_EFETCH})

    records = await client.fetch_records(["38000001"])

    assert len(records) == 1
    record = records[0]
    assert record.pmid == "38000001"
    assert record.title == "Robust meta-analysis of diagnostic accuracy"
    assert record.year == 2024
    assert record.journal == "Radiology"
    assert record.authors == ["Kim JK", "Lee ML"]
    assert record.doi == "10.1148/radiol.202412345"
    assert "FOUND A HIGH ACCURACY." in record.abstract.upper()
    assert record.publication_types == ["Journal Article", "Meta-Analysis"]
    assert record.is_open_access is True
    assert record.withdrawn is False


@pytest.mark.asyncio
async def test_fetch_records_empty_pmids_returns_empty():
    client = make_client({})
    assert await client.fetch_records([]) == []


@pytest.mark.asyncio
async def test_fetch_records_missing_abstract_and_year_are_none():
    xml = """<?xml version="1.0" ?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>2</PMID>
          <Article>
            <ArticleTitle>No abstract here</ArticleTitle>
            <Journal><JournalIssue><PubDate><Month>Mar</Month></PubDate></JournalIssue></Journal>
            <AuthorList>
              <Author><CollectiveName>Global Health Group</CollectiveName></Author>
            </AuthorList>
          </Article>
          <ArticleIdList>
            <ArticleId IdType="pubmed">2</ArticleId>
          </ArticleIdList>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    client = make_client({"efetch.fcgi": xml})

    records = await client.fetch_records(["2"])

    assert records[0].abstract is None
    assert records[0].year is None
    assert records[0].journal is None
    # 集体作者走 CollectiveName。
    assert records[0].authors == ["Global Health Group"]
    assert records[0].publication_types == []
    assert records[0].is_open_access is False


@pytest.mark.asyncio
async def test_fetch_records_detects_withdrawn_record():
    xml = """<?xml version="1.0" ?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>555</PMID>
          <Article>
            <ArticleTitle>A retracted study</ArticleTitle>
            <Journal><JournalIssue><PubDate><Year>2020</Year></PubDate></JournalIssue></Journal>
          </Article>
          <CommentsCorrectionsList>
            <CommentsCorrections RefType="RetractionIn">
              <RefSource>Ann Med. 2022</RefSource>
            </CommentsCorrections>
          </CommentsCorrectionsList>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>
    """
    client = make_client({"efetch.fcgi": xml})

    records = await client.fetch_records(["555"])

    assert records[0].withdrawn is True


# ---------------------------------------------------------------------------
# 网络异常
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_raises_pubmed_timeout():
    client = fast_backoff(
        make_client({"esearch.fcgi": httpx.TimeoutException("timed out")})
    )

    with pytest.raises(PubMedTimeoutError):
        await client.search("cancer")


@pytest.mark.asyncio
async def test_connection_error_raises_pubmed_connection():
    client = fast_backoff(make_client({"esearch.fcgi": httpx.ConnectError("refused")}))

    with pytest.raises(PubMedConnectionError):
        await client.search("cancer")


@pytest.mark.asyncio
async def test_retry_after_429_then_success():
    # 先返回 429，重试后成功；验证重试逻辑而非被 429 直接击穿。
    class RetryHTTP:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []
            self.count = 0

        async def get(self, url: str, params: dict[str, str]) -> httpx.Response:
            self.calls.append((url, params))
            self.count += 1
            if self.count == 1:
                return httpx.Response(429, text="rate limited")
            return httpx.Response(
                200, text='{"esearchresult":{"count":"1","idlist":["777"]}}'
            )

    retry_http = RetryHTTP()
    client = fast_backoff(
        PubMedClient(
            http_client=retry_http,  # type: ignore[arg-type]
            rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        )
    )

    result = await client.search("diabetes")

    assert retry_http.count == 2
    assert result.pmids == ["777"]


@pytest.mark.asyncio
async def test_persistent_429_raises_rate_limit_error():
    class Always429:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, str]]] = []

        async def get(self, url: str, params: dict[str, str]) -> httpx.Response:
            self.calls.append((url, params))
            return httpx.Response(429, text="rate limited")

    client = fast_backoff(
        PubMedClient(
            http_client=Always429(),  # type: ignore[arg-type]
            rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        )
    )

    with pytest.raises(PubMedRateLimitError):
        await client.search("cancer")


# ---------------------------------------------------------------------------
# 非法 XML / JSON
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_xml_raises_response_error():
    client = make_client({"efetch.fcgi": "<PubmedArticleSet><broken>"})

    with pytest.raises(PubMedResponseError, match="invalid XML"):
        await client.fetch_records(["1"])


@pytest.mark.asyncio
async def test_invalid_json_raises_response_error():
    client = make_client({"esearch.fcgi": "not json at all"})

    with pytest.raises(PubMedResponseError, match="non-JSON"):
        await client.search("cancer")


# ---------------------------------------------------------------------------
# 缓存
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cache_hit_avoids_repeat_request():
    http = FakeHTTPClient({"esearch.fcgi": esearch_payload(["1"])})
    client = PubMedClient(
        http_client=http,  # type: ignore[arg-type]
        rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        cache=TTLCache(),
    )

    first = await client.search("cancer", use_cache=True)
    second = await client.search("cancer", use_cache=True)

    assert first.pmids == second.pmids == ["1"]
    assert len(http.calls) == 1


@pytest.mark.asyncio
async def test_efetch_cache_hit_avoids_repeat_request():
    http = FakeHTTPClient({"efetch.fcgi": SAMPLE_EFETCH})
    client = PubMedClient(
        http_client=http,  # type: ignore[arg-type]
        rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        cache=TTLCache(),
    )

    await client.fetch_records(["38000001"], use_cache=True)
    await client.fetch_records(["38000001"], use_cache=True)

    assert len(http.calls) == 1


@pytest.mark.asyncio
async def test_disable_cache_repeats_request():
    http = FakeHTTPClient({"esearch.fcgi": esearch_payload(["1"])})
    client = PubMedClient(
        http_client=http,  # type: ignore[arg-type]
        rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        cache=TTLCache(),
    )

    await client.search("cancer", use_cache=False)
    await client.search("cancer", use_cache=False)

    assert len(http.calls) == 2


# ---------------------------------------------------------------------------
# RateLimiter / 工具
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_limiter_enforces_minimum_interval():
    import time

    limiter = RateLimiter(interval_seconds=0.05)
    start = time.monotonic()
    await limiter.wait()
    await limiter.wait()
    elapsed = time.monotonic() - start
    assert elapsed >= 0.05


def test_normalize_query_term_collapses_whitespace():
    assert _normalize_query_term("  cancer   AND   diabetes  ") == "cancer AND diabetes"


def test_cache_eviction_keeps_bounded_size():
    cache = TTLCache(max_entries=3)
    for i in range(5):
        cache.set(f"k{i}", i)
    assert len(cache) <= 3


# ---------------------------------------------------------------------------
# 回归测试：prism-scan 修复
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_esummary_cache_immune_to_caller_mutation():
    """回归：调用方修改 fetch_summary 返回值不得污染缓存。

    修复前 result 直接入缓存，调用方原地修改（如补字段）会让后续
    所有缓存命中返回被篡改数据；修复后存取两端均深拷贝。
    """
    client = make_client(
        {
            "esummary.fcgi": esummary_payload(
                {
                    "123": {
                        "title": "Original Title",
                        "fulljournalname": "J Med",
                        "pubdate": "2024",
                        "authors": [],
                        "pubtype": [],
                        "articleids": [],
                    },
                }
            )
        }
    )
    first = await client.fetch_summary(["123"])
    # 调用方恶意/无意修改返回的 dict
    first["123"]["title"] = "TAMPERED"
    # 第二次调用应命中缓存，但返回的是独立副本，未被污染
    second = await client.fetch_summary(["123"])
    assert second["123"]["title"] == "Original Title"
    # 同一 key 的两次命中也不共享引用
    third = await client.fetch_summary(["123"])
    third["123"]["journal"] = "MUTATED"
    fourth = await client.fetch_summary(["123"])
    assert fourth["123"]["journal"] == "J Med"


@pytest.mark.asyncio
async def test_retry_after_capped_at_30_seconds():
    """回归：429 的 Retry-After 头有 30s 上限，避免单请求挂起过久。

    修复前直接 sleep(float(retry_after))，NCBI 若返回 3600 会让请求
    挂起一小时；修复后 min(..., 30.0)。
    """
    sleeps: list[float] = []

    class RetryAfterHTTP:
        def __init__(self) -> None:
            self.count = 0

        async def get(self, url: str, params: dict[str, str]) -> httpx.Response:
            self.count += 1
            if self.count == 1:
                return httpx.Response(
                    429, headers={"Retry-After": "3600"}, text="rate limited"
                )
            return httpx.Response(
                200, text='{"esearchresult":{"count":"1","idlist":["777"]}}'
            )

    async def _capture_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    client = PubMedClient(
        http_client=RetryAfterHTTP(),  # type: ignore[arg-type]
        rate_limiter=InstantRateLimiter(),  # type: ignore[arg-type]
        cache=TTLCache(),
    )
    client._sleep_limited = _capture_sleep  # type: ignore[method-assign]

    result = await client.search("cancer")
    assert result.pmids == ["777"]
    assert sleeps == [30.0], f"期望 Retry-After 被截断为 30s，实际 {sleeps}"
