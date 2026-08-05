"""BibTeX 序列化单元测试。

覆盖 citation key 规范（FirstAuthorLastName_Year_OneWord）、特殊字符转义、
verified 三字段输出与作者拼接。
"""

from app.modules.literature_search.bibtex import citation_key, to_bibtex
from app.modules.literature_search.schema import CitationItem


def _item(**overrides) -> CitationItem:
    defaults: dict = {
        "pmid": "39000401",
        "doi": "10.1016/j.example.2024.01.001",
        "title": "Validation of neural networks in mammography",
        "authors": ["Kim J", "Lee S"],
        "journal": "Nature Medicine",
        "year": 2024,
        "verified": True,
        "verified_by": "pubmed",
        "verified_on": "2026-08-05T00:00:00+00:00",
    }
    defaults.update(overrides)
    return CitationItem(**defaults)


def test_citation_key_uses_first_author_year_and_first_word():
    item = _item()
    assert citation_key(item) == "Kim_2024_Validation"


def test_citation_key_uses_unknown_when_no_author_and_nd_when_no_year():
    item = _item(authors=[], year=None, title="A study on cancer")
    assert citation_key(item) == "Unknown_n.d._A"


def test_citation_key_falls_back_to_ref_when_title_is_non_ascii():
    item = _item(title="癌症的机制研究")
    assert citation_key(item) == "Kim_2024_Ref"


def test_to_bibtex_includes_verified_fields_and_escapes():
    text = to_bibtex([_item(title="50% of #cases")])

    assert "@article{Kim_2024_50," in text
    assert "  author = {Kim J and Lee S}," in text
    assert "  title = {50\\% of \\#cases}," in text
    assert "  verified = {true}," in text
    assert "  verified_by = {pubmed}," in text
    # verified_on 是条目最后一个字段，BibTeX 末行不带逗号
    assert "  verified_on = {2026-08-05T00:00:00+00:00}\n}" in text


def test_to_bibtex_unverified_item_outputs_false():
    text = to_bibtex([_item(verified=False, verified_by=None, verified_on=None)])

    assert "  verified = {false}," in text
    assert "  verified_by = {}," in text
    # verified_on 为末行，不带逗号
    assert "  verified_on = {}\n}" in text


def test_to_bibtex_escapes_special_characters_in_values():
    text = to_bibtex([_item(title="A&B {C} _D_", journal="J. % of Med")])

    assert "title = {A\\&B \\{C\\} \\_D\\_}," in text
    assert "journal = {J. \\% of Med}," in text
