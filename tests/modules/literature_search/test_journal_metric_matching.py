"""AC-15—18：确定性期刊匹配。"""

from types import SimpleNamespace

from app.modules.literature_search.journal_metric_matching import match_journal_metric
from app.modules.literature_search.schema import CitationItem


def candidate(
    key: str, *, issn: str | None = None, name: str | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        journal_key=key,
        issn_l=None,
        issn=issn,
        eissn=None,
        normalized_journal_name=name,
    )


def test_issn_match_precedes_title_match() -> None:
    item = CitationItem(pmid="1", journal="Title B", issn="2049-3630")
    result = match_journal_metric(
        item, [candidate("A", issn="2049-3630"), candidate("B", name="title b")]
    )
    assert (result.status, result.journal_key, result.method) == (
        "matched",
        "A",
        "issn_exact",
    )


def test_ambiguous_top_priority_match_is_hidden() -> None:
    item = CitationItem(pmid="1", issn="2049-3630")
    result = match_journal_metric(
        item, [candidate("A", issn="2049-3630"), candidate("B", issn="2049-3630")]
    )
    assert result.status == "ambiguous" and result.journal_key is None


def test_legacy_title_exact_match() -> None:
    result = match_journal_metric(
        CitationItem(pmid="1", journal="Example Journal"),
        [candidate("A", name="example journal")],
    )
    assert result.method == "normalized_title_exact"


def test_similar_title_is_not_fuzzy_matched() -> None:
    result = match_journal_metric(
        CitationItem(pmid="1", journal="Example Journals"),
        [candidate("A", name="example journal")],
    )
    assert result.status == "not_found"
