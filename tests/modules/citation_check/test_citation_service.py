"""citation_check service 单元测试。

使用替身 verifier，验证编排逻辑：提取 -> 校验 -> 汇总统计，以及反幻觉
边界（不可验证的引用保持 verified=false）。
"""

from __future__ import annotations

from datetime import UTC, datetime

from app.modules.citation_check.schema import (
    CitationAuditItem,
    CitationCheckRequest,
    CitationCheckResult,
)
from app.modules.citation_check.service import CitationCheckService


class FakeVerifier:
    """替身校验器：按 identifier 判定是否校验成功。"""

    def __init__(self, verified_ids: set[str]) -> None:
        self.verified_ids = verified_ids
        self.calls: list[str] = []

    async def verify_item(self, item: CitationAuditItem) -> CitationAuditItem:
        self.calls.append(item.identifier)
        if item.identifier in self.verified_ids:
            item.verified = True
            item.verified_by = "pubmed"
            item.verified_on = datetime.now(UTC).isoformat()
            item.matched = item.identifier
        else:
            item.notes.append("未找到")
        return item


async def test_check_builds_audit_report_with_summary():
    service = CitationCheckService(verifier=FakeVerifier({"39000401"}))
    result = await service.check(
        CitationCheckRequest(text="PMID: 39000401 and PMID: 99999999")
    )

    assert isinstance(result, CitationCheckResult)
    assert len(result.items) == 2
    assert result.summary.total == 2
    assert result.summary.verified == 1
    assert result.summary.unverified == 1

    verified = [item for item in result.items if item.identifier == "39000401"][0]
    assert verified.verified is True
    assert verified.verified_by == "pubmed"
    assert verified.matched == "39000401"

    unverified = [item for item in result.items if item.identifier == "99999999"][0]
    assert unverified.verified is False
    assert unverified.notes == ["未找到"]


async def test_check_with_no_references_returns_empty_report():
    service = CitationCheckService(verifier=FakeVerifier(set()))
    result = await service.check(CitationCheckRequest(text="纯文本，没有引用。"))

    assert result.items == []
    assert result.summary.total == 0
    assert result.summary.verified == 0
    assert result.summary.unverified == 0
