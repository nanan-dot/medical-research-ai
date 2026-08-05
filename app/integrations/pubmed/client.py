"""PubMed E-utilities 客户端。

核心能力：
- ESearch / ESummary / EFetch 三个官方端点；
- API Key + Email 参数；
- 超时、重试、限流（RateLimiter）、缓存（TTLCache）；
- 解析错误标准化（非法 XML/JSON、响应结构变化）；
- 请求日志（不记录 query 原始布尔表达式以外无敏感信息，且不输出 XML 正文）。

反幻觉协议：所有 PMID/DOI/标题/年份/作者只来自 API 响应，绝不从记忆补全。
本模块不直接暴露原始 XML，解析结果统一收敛到 schemas.PubMedRecord。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any
from xml.etree import ElementTree

import httpx
from pydantic import SecretStr

from app.integrations.pubmed.cache import TTLCache
from app.integrations.pubmed.exceptions import (
    PubMedConfigurationError,
    PubMedConnectionError,
    PubMedError,
    PubMedOperationError,
    PubMedRateLimitError,
    PubMedResponseError,
    PubMedTimeoutError,
)
from app.integrations.pubmed.rate_limit import RateLimiter
from app.integrations.pubmed.schemas import PubMedConfig, PubMedRecord, PubMedSearchResult

logger = logging.getLogger(__name__)

# NCBI 对无效 API Key 返回 401，Email 缺失可能被 403 拒绝；这些状态码不重试。
_NO_RETRY_STATUS_CODES = {401, 403}
# 5xx 与 429 属于可重试状态。
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

_DEFAULT_RETRY_COUNT = 3
_DEFAULT_MAX_PMIDS_PER_FETCH = 200


def _ln(tag: str) -> str:
    """去掉 XML 命名空间前缀，返回 local-name。

    设计说明：NCBI 的 efetch.fcgi 默认输出无命名空间的 XML，而 Atom 格式
    输出带命名空间；统一按 local-name 匹配可同时兼容两者，避免响应结构变化
    导致解析失败。
    """
    return tag.rsplit("}", 1)[-1]


def _child(element: ElementTree.Element, name: str) -> ElementTree.Element | None:
    """返回直接子元素中第一个 local-name 匹配的子节点。"""
    for child in element:
        if _ln(child.tag) == name:
            return child
    return None


def _iter_local(element: ElementTree.Element, name: str) -> list[ElementTree.Element]:
    """返回所有后代中 local-name 匹配的子节点（深度优先）。"""
    return [child for child in element.iter() if _ln(child.tag) == name]


def _normalize_query_term(value: str) -> str:
    """压缩空白并去除首尾空白，避免把含多余空白的表达式送入请求。

    设计说明：query 来自上游构造器时已经过合法性校验，这里只做传输前的
    归一化，不解析语义、不新增/删除任何词项。
    """
    return " ".join(value.split())


class PubMedClient:
    """对 NCBI E-utilities 的异步客户端，仅暴露结构化接口。"""

    def __init__(
        self,
        config: PubMedConfig | None = None,
        *,
        http_client: httpx.AsyncClient | None = None,
        cache: TTLCache | None = None,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self.config = config or PubMedConfig()
        self._owns_http_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            timeout=self.config.timeout_seconds,
            follow_redirects=True,
        )
        # 有 API Key 时 NCBI 允许 10 req/s，间隔可放宽；无 Key 保持 350ms。
        effective_interval = self.config.rate_limit_seconds
        self._rate_limiter = rate_limiter or RateLimiter(effective_interval)
        self._cache = cache if cache is not None else TTLCache()

    @classmethod
    def from_settings(cls, app_settings: Any = None) -> "PubMedClient":
        """从应用 Settings 构建客户端。

        缺省时使用 app.core.config.settings 的单例；字段缺失时退化为空配置。
        设计说明：与 paperqa2/ollama 的 from_settings 风格保持一致，把
        Settings 对象作为唯一参数，避免这里耦合具体 Settings 实现。
        """
        if app_settings is None:
            from app.core.config import settings as app_settings
        api_key = getattr(app_settings, "PUBMED_API_KEY", "") or ""
        email = getattr(app_settings, "PUBMED_EMAIL", "") or ""
        timeout = getattr(app_settings, "PUBMED_TIMEOUT_SECONDS", None) or 20.0
        config = PubMedConfig(
            email=email or None,
            api_key=SecretStr(api_key) if api_key else None,
            rate_limit_seconds=0.1 if api_key else 0.35,
            timeout_seconds=timeout,
        )
        return cls(config=config)

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        retmax: int = 20,
        retstart: int = 0,
        sort: str | None = None,
        use_cache: bool = True,
    ) -> PubMedSearchResult:
        """ESearch：返回 PMID 列表及总数。"""
        query = _normalize_query_term(query)
        if not query:
            raise PubMedConfigurationError("PubMed search query must be non-empty")

        params = self._common_params(
            {
                "db": "pubmed",
                "term": query,
                "retmax": str(max(1, int(retmax))),
                "retstart": str(max(0, int(retstart))),
                "retmode": "json",
            }
        )
        if sort:
            params["sort"] = sort

        cache_key = self._cache_key("esearch", params)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("PubMed ESearch cache hit query=%r", query[:80])
                return cached

        payload = await self._get_json("esearch.fcgi", params)
        result = self._parse_esearch(payload)
        if use_cache:
            self._cache.set(cache_key, result)
        logger.info("PubMed ESearch done query=%r hits=%d", query[:120], result.total_count)
        return result

    async def fetch_summary(
        self,
        pmids: list[str],
        *,
        use_cache: bool = True,
    ) -> dict[str, dict[str, Any]]:
        """ESummary：批量返回 PMID -> 摘要字段字典（标准化后的元数据）。"""
        ids = self._normalize_pmids(pmids)
        if not ids:
            return {}
        params = self._common_params(
            {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
        )
        cache_key = self._cache_key("esummary", params)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("PubMed ESummary cache hit ids=%d", len(ids))
                return cached

        payload = await self._get_json("esummary.fcgi", params)
        result = self._parse_esummary(payload)
        if use_cache:
            self._cache.set(cache_key, result)
        logger.info("PubMed ESummary done ids=%d returned=%d", len(ids), len(result))
        return result

    async def fetch_records(
        self,
        pmids: list[str],
        *,
        use_cache: bool = True,
    ) -> list[PubMedRecord]:
        """EFetch：按 PMID 获取完整记录并标准化为 PubMedRecord 列表。

        设计说明：摘要、文献类型、开放全文标记只存在于 EFetch XML 中，
        ESummary 不含这些字段，因此 fetch_records 内部走 EFetch 而不是复用
        fetch_summary。
        """
        ids = self._normalize_pmids(pmids)
        if not ids:
            return []
        # EFetch 一次最多 200 个 PMID，超出时分批请求。
        chunks = [
            ids[i : i + _DEFAULT_MAX_PMIDS_PER_FETCH]
            for i in range(0, len(ids), _DEFAULT_MAX_PMIDS_PER_FETCH)
        ]
        records: list[PubMedRecord] = []
        for chunk in chunks:
            records.extend(await self._fetch_records_chunk(chunk, use_cache=use_cache))
        return records

    async def aclose(self) -> None:
        if self._owns_http_client:
            await self._http_client.aclose()

    async def __aenter__(self) -> "PubMedClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # EFetch 内部分片
    # ------------------------------------------------------------------

    async def _fetch_records_chunk(self, ids: list[str], *, use_cache: bool) -> list[PubMedRecord]:
        params = self._common_params(
            {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
        )
        cache_key = self._cache_key("efetch", params)
        if use_cache:
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug("PubMed EFetch cache hit ids=%d", len(ids))
                return list(cached)

        xml_text = await self._get_xml("efetch.fcgi", params)
        records = self._parse_efetch(xml_text)
        if use_cache:
            self._cache.set(cache_key, list(records))
        logger.info("PubMed EFetch done ids=%d returned=%d", len(ids), len(records))
        return records

    # ------------------------------------------------------------------
    # 底层 HTTP 调用
    # ------------------------------------------------------------------

    def _common_params(self, base: dict[str, str]) -> dict[str, str]:
        params = dict(base)
        params["tool"] = self.config.tool
        if self.config.email:
            params["email"] = self.config.email
        if self.config.api_key:
            params["api_key"] = self.config.api_key.get_secret_value()
        return params

    @staticmethod
    def _cache_key(endpoint: str, params: dict[str, str]) -> str:
        """缓存键：端点 + 规范化参数（排除 email/api_key/tool 等非语义参数）。"""
        significant = {
            k: v for k, v in params.items() if k not in {"email", "api_key", "tool"}
        }
        raw = json.dumps(significant, sort_keys=True, ensure_ascii=True)
        return f"{endpoint}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"

    async def _get_json(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        text = await self._request(endpoint, params)
        try:
            payload = json.loads(text)
        except (ValueError, TypeError) as error:
            raise PubMedResponseError(
                "NCBI returned non-JSON content for ESummary/ESearch"
            ) from error
        if not isinstance(payload, dict):
            raise PubMedResponseError("NCBI returned a non-object JSON payload")
        return payload

    async def _get_xml(self, endpoint: str, params: dict[str, str]) -> str:
        return await self._request(endpoint, params)

    async def _request(
        self,
        endpoint: str,
        params: dict[str, str],
        *,
        retry_count: int = _DEFAULT_RETRY_COUNT,
    ) -> str:
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        last_error: Exception | None = None
        for attempt in range(1, retry_count + 1):
            await self._rate_limiter.wait()
            logger.debug("PubMed request endpoint=%s attempt=%d/%d", endpoint, attempt, retry_count)
            try:
                response = await self._http_client.get(url, params=params)
            except httpx.TimeoutException as error:
                last_error = error
                logger.warning("PubMed timeout endpoint=%s attempt=%d", endpoint, attempt)
                if attempt < retry_count:
                    await self._backoff(attempt)
                    continue
                raise PubMedTimeoutError(
                    f"PubMed request timed out after {retry_count} attempts"
                ) from error
            except httpx.TransportError as error:
                last_error = error
                logger.warning("PubMed connection failed endpoint=%s attempt=%d", endpoint, attempt)
                if attempt < retry_count:
                    await self._backoff(attempt)
                    continue
                raise PubMedConnectionError(
                    f"Could not reach NCBI after {retry_count} attempts"
                ) from error

            status_code = response.status_code
            if status_code == 429 or status_code in _RETRYABLE_STATUS_CODES:
                last_error = PubMedRateLimitError(
                    f"NCBI returned HTTP {status_code}",
                    detail={"status_code": status_code, "attempt": attempt},
                )
                logger.warning(
                    "PubMed retryable status endpoint=%s status=%d attempt=%d",
                    endpoint,
                    status_code,
                    attempt,
                )
                if attempt < retry_count:
                    # 429 时尊重 NCBI 的 Retry-After 头，否则指数退避。
                    retry_after = response.headers.get("Retry-After")
                    delay = (
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else 2**attempt
                    )
                    await self._sleep_limited(delay)
                    continue
                raise PubMedRateLimitError(
                    f"NCBI rate limited (HTTP {status_code}) after {retry_count} attempts",
                    detail={"status_code": status_code},
                ) from last_error
            if status_code in _NO_RETRY_STATUS_CODES:
                raise PubMedError(
                    "NCBI rejected the request; check the API key and email settings",
                    detail={"status_code": status_code},
                )
            if status_code >= 400:
                raise PubMedError(
                    f"NCBI returned HTTP {status_code}",
                    detail={"status_code": status_code},
                )

            text = response.text
            if not text or not text.strip():
                raise PubMedResponseError("NCBI returned an empty response body")
            return text

        # retry_count 必须 >= 1；此分支理论上不可达，防御性兜底。
        assert last_error is not None
        raise PubMedOperationError("PubMed request failed") from last_error

    async def _backoff(self, attempt: int) -> None:
        await self._sleep_limited(2**attempt)

    async def _sleep_limited(self, seconds: float) -> None:
        # 限流器已经保证请求间隔，这里退避睡完即可；同时避免 0 长度 sleep。
        await asyncio.sleep(max(0.0, seconds))

    # ------------------------------------------------------------------
    # 响应解析
    # ------------------------------------------------------------------

    def _parse_esearch(self, payload: dict[str, Any]) -> PubMedSearchResult:
        """解析 ESearch JSON。

        处理两种已知的响应变化：新版返回 result.esearchresult，历史版本也可能
        直接在顶层出现 esearchresult 字段；缺省容错为空结果。
        """
        esearch = payload.get("esearchresult")
        if not isinstance(esearch, dict):
            esearch = payload
        idlist_raw = esearch.get("idlist", [])
        if isinstance(idlist_raw, str):
            idlist_raw = [idlist_raw]
        if not isinstance(idlist_raw, list):
            idlist_raw = []
        pmids = [str(value) for value in idlist_raw if str(value).strip()]
        try:
            total_count = int(esearch.get("count", len(pmids)))
        except (TypeError, ValueError):
            total_count = len(pmids)
        return PubMedSearchResult(
            pmids=pmids,
            total_count=max(0, total_count),
            query_key=esearch.get("querykey") if isinstance(esearch.get("querykey"), str) else None,
            web_env=esearch.get("webenv") if isinstance(esearch.get("webenv"), str) else None,
        )

    def _parse_esummary(self, payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """解析 ESummary JSON，保留标准化后的字段子集。"""
        result = payload.get("result")
        if not isinstance(result, dict):
            raise PubMedResponseError("NCBI ESummary response missing 'result'")
        uids = result.get("uids")
        if not isinstance(uids, list):
            uids = [key for key in result if key != "uids"]
        out: dict[str, dict[str, Any]] = {}
        for uid in uids:
            entry = result.get(str(uid))
            if not isinstance(entry, dict):
                continue
            out[str(uid)] = {
                "title": _first_str(entry.get("title")),
                "authors": _extract_authors(entry.get("authors")),
                "journal": _first_str(entry.get("fulljournalname")) or _first_str(
                    entry.get("source")
                ),
                "year": _to_int(entry.get("pubdate") or entry.get("epubdate")),
                "pubtypes": _extract_pubtypes(entry.get("pubtype")),
                "doi": _extract_doi(entry.get("articleids")),
            }
        return out

    def _parse_efetch(self, xml_text: str) -> list[PubMedRecord]:
        """解析 EFetch XML 并标准化为 PubMedRecord 列表。

        必须处理的异常：
        - 非法/非 XML 响应 -> PubMedResponseError；
        - 单条记录缺 abstract / 缺 year / 缺 journal 时用 None 兜底；
        - 作者格式复杂（集体作者、带后缀、姓名拆分）统一收敛为 "Last FM" 形式；
        - 撤回记录通过 CommentsCorrectionsList/RefType=RetractionIn 标记。
        """
        try:
            root = ElementTree.fromstring(xml_text)
        except ElementTree.ParseError as error:
            raise PubMedResponseError("NCBI returned invalid XML") from error

        records: list[PubMedRecord] = []
        for article in _iter_local(root, "PubmedArticle"):
            record = self._extract_record(article)
            if record is not None:
                records.append(record)
        return records

    def _extract_record(self, article: ElementTree.Element) -> PubMedRecord | None:
        citation = _child(article, "MedlineCitation")
        if citation is None:
            return None

        pmid_el = _child(citation, "PMID")
        pmid = _text_or_none(pmid_el)
        if not pmid:
            return None

        article_el = _child(citation, "Article")
        title = None
        abstract = None
        journal = None
        year: int | None = None
        pubtypes: list[str] = []
        if article_el is not None:
            title_el = _child(article_el, "ArticleTitle")
            title = _text_or_none(title_el)
            abstract = _extract_abstract(article_el)
            journal = _extract_journal(citation)
            year = _extract_year(article_el)
            pubtypes = _extract_publication_types(article_el)
        authors = _extract_author_list(article_el)

        doi = None
        article_id_el = _child(citation, "ArticleIdList")
        if article_id_el is not None:
            for id_el in _iter_local(article_id_el, "ArticleId"):
                if (id_el.get("IdType") or "").lower() == "doi":
                    doi = _text_or_none(id_el)
                    break

        withdrawn = _is_withdrawn(citation)
        is_open_access = _is_open_access(citation)
        return PubMedRecord(
            pmid=pmid,
            doi=doi,
            title=title,
            authors=authors,
            journal=journal,
            year=year,
            abstract=abstract,
            publication_types=pubtypes,
            is_open_access=is_open_access,
            withdrawn=withdrawn,
        )

    # ------------------------------------------------------------------
    # 工具
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_pmids(pmids: list[str]) -> list[str]:
        seen: list[str] = []
        for value in pmids:
            cleaned = str(value).strip()
            if cleaned.isdigit() and cleaned not in seen:
                seen.append(cleaned)
        return seen


def _text_or_none(element: ElementTree.Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    text = " ".join(element.text.split())
    return text or None


def _first_str(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        return cleaned or None
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, str):
        # pubdate 形如 "2024 Jan 15" 或 "2024"，取首个四位数年份。
        match = re.search(r"\b(1[89]\d{2}|20\d{2})\b", value)
        return int(match.group(1)) if match else None
    return value if isinstance(value, int) else None


def _extract_authors(value: Any) -> list[str]:
    """从 ESummary 的 authors 数组提取标准名。"""
    if not isinstance(value, list):
        return []
    names: list[str] = []
    for author in value:
        if not isinstance(author, dict):
            continue
        name = author.get("name")
        if isinstance(name, str) and name.strip():
            names.append(" ".join(name.split()))
    return names


def _extract_pubtypes(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if isinstance(item, str) and item.strip()]
    return []


def _extract_doi(articleids: Any) -> str | None:
    """从 ESummary 的 articleids 数组提取 DOI。"""
    if not isinstance(articleids, list):
        return None
    for item in articleids:
        if isinstance(item, dict) and item.get("idtype") == "doi":
            value = item.get("value")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_abstract(article_el: ElementTree.Element) -> str | None:
    """EFetch 摘要可能拆成多个 AbstractText 段，按出现顺序拼接。"""
    abstract_el = _child(article_el, "Abstract")
    if abstract_el is None:
        return None
    parts: list[str] = []
    for text_el in _iter_local(abstract_el, "AbstractText"):
        label = text_el.get("Label")
        text = " ".join((text_el.text or "").split())
        if not text:
            continue
        parts.append(f"{label}: {text}" if label else text)
    if not parts:
        return None
    return " ".join(parts)


def _extract_journal(citation: ElementTree.Element) -> str | None:
    article_el = _child(citation, "Article")
    if article_el is None:
        return None
    journal_el = _child(article_el, "Journal")
    if journal_el is None:
        return None
    title_el = _child(journal_el, "Title")
    return _text_or_none(title_el)


def _extract_year(article_el: ElementTree.Element) -> int | None:
    """从 ArticleDate 或 JournalIssue 中提取年份，缺失返回 None。"""
    for date_el in _iter_local(article_el, "ArticleDate"):
        year = _to_int(_text_or_none(_child(date_el, "Year")))
        if year is not None:
            return year
    journal_el = _child(article_el, "Journal")
    if journal_el is not None:
        journal_issue = _child(journal_el, "JournalIssue")
        if journal_issue is not None:
            for pub_date in _iter_local(journal_issue, "PubDate"):
                year = _to_int(_text_or_none(_child(pub_date, "Year")))
                if year is not None:
                    return year
    return None


def _extract_publication_types(article_el: ElementTree.Element) -> list[str]:
    types: list[str] = []
    pub_type_list = _child(article_el, "PublicationTypeList")
    if pub_type_list is not None:
        for el in _iter_local(pub_type_list, "PublicationType"):
            text = _text_or_none(el)
            if text:
                types.append(text)
    return types


def _extract_author_list(article_el: ElementTree.Element | None) -> list[str]:
    if article_el is None:
        return []
    authors: list[str] = []
    author_list = _child(article_el, "AuthorList")
    if author_list is None:
        return []
    for author_el in _iter_local(author_list, "Author"):
        # 集体作者：无 LastName，使用 CollectiveName。
        collective = _child(author_el, "CollectiveName")
        if collective is not None and (collective.text or "").strip():
            authors.append(" ".join((collective.text or "").split()))
            continue
        last = _text_or_none(_child(author_el, "LastName"))
        fore = _text_or_none(_child(author_el, "ForeName"))
        if not last:
            continue
        initials = _text_or_none(_child(author_el, "Initials"))
        # 标准化为 "LastName FM" 形式，缺失部分不伪造。
        if initials:
            authors.append(f"{last} {initials}")
        elif fore:
            authors.append(f"{last} {fore}")
        else:
            authors.append(last)
    return authors


def _is_withdrawn(citation: ElementTree.Element) -> bool:
    """识别撤回记录。

    NCBI 在 <CommentsCorrectionsList> 中用 RefType="RetractionIn" 的条目标记
    "本文被 XX 撤回"；检测到即视为 withdrawn=True。注意这是元数据标记，
    不等于直接删除 PMID。
    """
    comments = _child(citation, "CommentsCorrectionsList")
    if comments is None:
        return False
    for item in _iter_local(comments, "CommentsCorrections"):
        if (item.get("RefType") or "").lower() == "retractionin":
            return True
    return False


def _is_open_access(citation: ElementTree.Element) -> bool:
    """通过 ArticleIdList 中存在 PMC id 判断是否为 PMC 收录的开放全文。"""
    article_id_list = _child(citation, "ArticleIdList")
    if article_id_list is None:
        return False
    for id_el in _iter_local(article_id_list, "ArticleId"):
        if (id_el.get("IdType") or "").upper() == "PMC":
            return True
    return False
