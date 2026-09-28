"""AC-08、17、18：期刊身份规范化边界。"""

from app.modules.literature_search.journal_metric_normalization import (
    is_valid_issn,
    normalize_issn,
    normalize_journal_name,
)


def test_invalid_issn_normalizes_to_none_and_does_not_match() -> None:
    assert normalize_issn("2049-3631") is None
    assert normalize_issn("abcd-efgh") is None
    assert normalize_issn(None) is None


def test_issn_accepts_spacing_hyphen_and_lowercase_x() -> None:
    assert normalize_issn(" 2434 561x ") == "2434-561X"
    assert is_valid_issn("2434-561X")


def test_title_normalization_is_exact_not_fuzzy() -> None:
    assert normalize_journal_name("Example: Journal") == "example journal"
    assert normalize_journal_name("Example Journals") != normalize_journal_name(
        "Example Journal"
    )
