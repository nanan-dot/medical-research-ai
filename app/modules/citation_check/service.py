"""citation_check — 审计编排

流程：提取引用 -> 逐个校验 -> 汇总统计。校验只信任真实 API 响应，任何
未找到/超时/服务不可用的引用都保留 verified=false。
"""

from __future__ import annotations

from app.modules.citation_check.extractor import extract_references
from app.modules.citation_check.schema import (
    CitationAuditItem,
    CitationAuditSummary,
    CitationCheckRequest,
    CitationCheckResult,
)
from app.modules.citation_check.verifier import CitationVerifier


class CitationCheckService:
    """引用真实性审计服务。"""

    def __init__(self, verifier: CitationVerifier | None = None) -> None:
        self.verifier = verifier or CitationVerifier()

    async def check(self, request: CitationCheckRequest) -> CitationCheckResult:
        """执行完整审计并返回报告。"""
        items = extract_references(request.text)
        verified_items: list[CitationAuditItem] = []
        for item in items:
            verified_items.append(await self.verifier.verify_item(item))
        summary = self._summarize(verified_items)
        return CitationCheckResult(items=verified_items, summary=summary)

    @staticmethod
    def _summarize(items: list[CitationAuditItem]) -> CitationAuditSummary:
        verified = sum(1 for item in items if item.verified)
        return CitationAuditSummary(
            total=len(items),
            verified=verified,
            unverified=len(items) - verified,
        )
