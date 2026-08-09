"""citation_check 真实网络集成测试（显式门控）。

运行方式：
    RUN_CITATION_CHECK_LIVE_TEST=1 pytest tests/integrations/test_citation_check_live.py -v

未设置该环境变量时全部跳过。校验使用真实 PubMed / CrossRef，验证反幻觉协议：
真实存在的 PMID/DOI 应标 verified=true，伪造的标识符应标 verified=false。
"""

import os

import pytest

from app.modules.citation_check.extractor import extract_references
from app.modules.citation_check.verifier import CitationVerifier

pytestmark = pytest.mark.integration

# 锚点：使用经典文献 PMID 与 DOI，均由真实服务校验结果决定，不手动编造验证结论。
KNOWN_PMID = "11731580"  # 高被引经典文献，PMID 在 PubMed 中长期存在
UNKNOWN_PMID = (
    "99999999"  # 8 位伪造 PMID：PubMed 未分配此编号，用于验证"查不到标 false"
)
KNOWN_DOI = "10.1038/nmeth.2089"  # Nature Methods 经典论文 DOI
UNKNOWN_DOI = "10.9999/does-not-exist-xyz"


def _skip_unless_enabled() -> None:
    if os.getenv("RUN_CITATION_CHECK_LIVE_TEST") != "1":
        pytest.skip(
            "set RUN_CITATION_CHECK_LIVE_TEST=1 to run live citation-check tests"
        )


@pytest.mark.asyncio
async def test_live_verifies_known_pmid():
    _skip_unless_enabled()
    items = extract_references(f"see PMID: {KNOWN_PMID}")
    async with CitationVerifier() as verifier:
        verified = await verifier.verify_item(items[0])

    assert verified.verified is True
    assert verified.verified_by == "pubmed"
    assert verified.matched == KNOWN_PMID


@pytest.mark.asyncio
async def test_live_does_not_verify_unknown_pmid():
    _skip_unless_enabled()
    items = extract_references(f"see PMID: {UNKNOWN_PMID}")
    async with CitationVerifier() as verifier:
        verified = await verifier.verify_item(items[0])

    assert verified.verified is False
    assert any("未找到" in note for note in verified.notes)


@pytest.mark.asyncio
async def test_live_verifies_known_doi_via_crossref():
    _skip_unless_enabled()
    items = extract_references(f"see doi: {KNOWN_DOI}")
    async with CitationVerifier() as verifier:
        verified = await verifier.verify_item(items[0])

    assert verified.verified is True
    assert verified.verified_by == "crossref"


@pytest.mark.asyncio
async def test_live_does_not_verify_unknown_doi():
    _skip_unless_enabled()
    items = extract_references(f"see doi: {UNKNOWN_DOI}")
    async with CitationVerifier() as verifier:
        verified = await verifier.verify_item(items[0])

    assert verified.verified is False
    assert any("未找到" in note for note in verified.notes)
