"""引用真实性校验器。

复用 app/integrations/pubmed 的 PubMedClient 校验 PMID，另用轻量 CrossRef
REST API 校验 DOI。两个来源都只把"真实 API 响应中存在"视为 verified=true；
超时、网络错误或未找到一律返回 verified=false 并附 notes，绝不伪造。

CrossRef 校验通过现有 httpx 依赖实现，不新增第三方库；错误处理遵循项目
约定（记录日志、结构化返回），不向调用方泄漏网络异常细节。
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.integrations.pubmed.client import PubMedClient
from app.integrations.pubmed.exceptions import PubMedError
from app.modules.citation_check.schema import CitationAuditItem

logger = logging.getLogger(__name__)

VERIFIED_BY_PUBMED = "pubmed"
VERIFIED_BY_CROSSREF = "crossref"

# CrossRef works API：HEAD 或 GET https://api.crossref.org/works/<DOI>，
# 返回 200 表示该 DOI 已注册。
_CROSSREF_BASE_URL = "https://api.crossref.org"
_CROSSREF_TIMEOUT_SECONDS = 15.0


class CitationVerifier:
    """对 PMID / DOI 引用做真实性校验。"""

    def __init__(
        self,
        *,
        pubmed_client: PubMedClient | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._pubmed = pubmed_client or PubMedClient.from_settings()
        self._http = http_client or httpx.AsyncClient(
            timeout=_CROSSREF_TIMEOUT_SECONDS, follow_redirects=True
        )
        self._owns_http = http_client is None

    async def verify_item(self, item: CitationAuditItem) -> CitationAuditItem:
        """校验单条引用并回填验证字段。

        校验成功时更新 verified/verified_by/verified_on/matched；失败时保留
        verified=false 并在 notes 中记录原因。
        """
        if item.kind == "pmid":
            return await self._verify_pmid(item)
        return await self._verify_doi(item)

    async def aclose(self) -> None:
        await self._pubmed.aclose()
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> "CitationVerifier":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # PMID 校验（PubMedClient）
    # ------------------------------------------------------------------

    async def _verify_pmid(self, item: CitationAuditItem) -> CitationAuditItem:
        if not item.identifier.isdigit():
            item.notes.append("PMID 必须为纯数字，无法校验")
            return item
        try:
            records = await self._pubmed.fetch_records([item.identifier])
        except PubMedError as exc:
            # 结构化记录为不可验证，不向调用方泄漏网络异常细节。
            logger.warning("citation_check PMID verification failed id=%s error=%s", item.identifier, exc)
            item.notes.append("PubMed 校验服务暂不可用，标记为未验证")
            return item
        if not records:
            item.notes.append("PubMed 未找到该 PMID")
            return item
        record = records[0]
        return self._mark_verified(item, VERIFIED_BY_PUBMED, record.pmid)

    # ------------------------------------------------------------------
    # DOI 校验（CrossRef）
    # ------------------------------------------------------------------

    async def _verify_doi(self, item: CitationAuditItem) -> CitationAuditItem:
        doi = item.identifier.lower()
        url = f"{_CROSSREF_BASE_URL}/works/{doi}"
        try:
            response = await self._http.get(url)
        except httpx.HTTPError as exc:
            logger.warning("citation_check DOI verification failed doi=%s error=%s", doi, exc)
            item.notes.append("CrossRef 校验服务暂不可用，标记为未验证")
            return item

        if response.status_code == 200:
            try:
                matched = self._extract_matched_doi(response.json()) or doi
            except ValueError:
                # CrossRef 返回非 JSON 内容（罕见），无法解析即为不可验证。
                logger.warning("citation_check DOI response was not JSON doi=%s", doi)
                item.notes.append("CrossRef 返回内容无法解析，标记为未验证")
                return item
            return self._mark_verified(item, VERIFIED_BY_CROSSREF, matched)
        if response.status_code == 404:
            item.notes.append("CrossRef 未找到该 DOI")
            return item
        item.notes.append(f"CrossRef 返回 HTTP {response.status_code}，标记为未验证")
        return item

    @staticmethod
    def _extract_matched_doi(payload: dict[str, Any]) -> str | None:
        """从 CrossRef 响应 message 中提取规范 DOI，便于审计报告展示。"""
        message = payload.get("message")
        if isinstance(message, dict):
            doi = message.get("DOI")
            if isinstance(doi, str) and doi.strip():
                return doi.strip()
        return None

    @staticmethod
    def _mark_verified(
        item: CitationAuditItem,
        source: str,
        matched: str,
    ) -> CitationAuditItem:
        """回填验证标记（唯一允许把 verified 置为 true 的路径）。"""
        item.verified = True
        item.verified_by = source
        item.verified_on = datetime.now(UTC).isoformat()
        item.matched = matched
        return item
