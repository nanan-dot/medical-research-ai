from app.modules.citation_check.consistency_checker import compare_metadata
from app.modules.citation_check.format_validator import validate_identifier
from app.modules.citation_check.statement_checker import check_statement
from app.modules.citation_check.extractor import extract_references


def test_l1_rejects_bad_identifiers_without_network() -> None:
    assert validate_identifier("doi", "not-a-doi").status == "invalid_format"
    assert validate_identifier("doi", "10.").status == "invalid_format"
    assert validate_identifier("doi", "10.9999/fake").status == "format_valid"
    assert validate_identifier("pmid", "123456789").status == "invalid_format"
    assert extract_references("PMID: 123456789")[0].identifier == "123456789"


def test_l3_reports_title_author_year_mismatch() -> None:
    result = compare_metadata(
        {"title": "Cancer therapy", "authors": ["Alice"], "year": 2022},
        {"title": "Cardiology trial", "authors": ["Bob"], "year": 2021},
    )
    assert result.status == "mismatch"
    assert result.differences


def test_statement_checker_marks_missing_and_topic_mismatch() -> None:
    no_citation = check_statement("治疗有效", [], topic="cancer")
    assert no_citation.status == "no_citation"
    mismatch = check_statement("心脏研究", ["doi:10.1/x"], topic="cancer")
    assert mismatch.status == "topic_mismatch"
    assert mismatch.replacement_suggested is False
