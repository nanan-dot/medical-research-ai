"""citation_check extractor 单元测试。

验证规则实现能识别 PMID/DOI 形态、去重，并正确规范化标识符。
"""

from app.modules.citation_check.extractor import extract_references


def test_extracts_pmid_and_doi_from_text():
    text = (
        "Recent work (PMID: 39000401) confirmed the finding. "
        "See also https://doi.org/10.1016/j.example.2024.01.001."
    )
    items = extract_references(text)

    kinds = {item.kind for item in items}
    assert kinds == {"pmid", "doi"}
    assert any(item.identifier == "39000401" for item in items)
    assert any(item.identifier == "10.1016/j.example.2024.01.001" for item in items)


def test_extracts_multiple_pmids_with_variants():
    text = "PubMed ID 123, PMID: 456, pubmed#789."
    items = extract_references(text)

    assert {item.identifier for item in items} == {"123", "456", "789"}


def test_deduplicates_duplicate_identifiers():
    text = "PMID: 39000401 and again PMID: 39000401."
    items = extract_references(text)

    assert len(items) == 1
    assert items[0].identifier == "39000401"


def test_does_not_match_random_numbers_or_doi_like_suffix():
    text = "The year 2024 had 100 cases; version 10.1000 not a doi."
    items = extract_references(text)

    # 版本号 "10.1000 not" 因后续不是合法的 DOI 后缀（需紧跟斜杠）不应被匹配。
    assert items == []


def test_empty_text_returns_no_items():
    assert extract_references("") == []
    assert extract_references("仅中文内容，没有引用标识符。") == []
