"""A3 deterministic evidence scoring acceptance tests."""

from app.modules.document_relocation.scoring import (
    compare_protected_tokens,
    score_candidate,
)


def test_exact_quote_has_complete_protected_token_match() -> None:
    result = score_candidate(
        "No benefit at 5 mg; HR 0.82 (95% CI 0.70-0.96).",
        "No benefit at 5 mg; HR 0.82 (95% CI 0.70-0.96).",
        prefix_similarity=1.0,
        suffix_similarity=1.0,
    )
    assert result.protected_token_status == "match"
    assert result.breakdown["quote_exactness"] == 1.0
    assert result.is_eligible


def test_changed_dose_or_effect_measure_blocks_candidate_confirmation() -> None:
    for candidate in [
        "No benefit at 50 mg; HR 0.82 (95% CI 0.70-0.96).",
        "No benefit at 5 mg; HR 1.82 (95% CI 0.70-0.96).",
    ]:
        result = score_candidate(
            "No benefit at 5 mg; HR 0.82 (95% CI 0.70-0.96).", candidate
        )
        assert result.protected_token_status == "mismatch"
        assert not result.is_eligible


def test_negation_direction_is_a_protected_expression() -> None:
    comparison = compare_protected_tokens(
        "Treatment did not increase risk", "Treatment increased risk"
    )
    assert comparison.status == "mismatch"
    assert "not" in comparison.missing


def test_score_breakdown_contains_no_source_quote() -> None:
    source = "Sensitive patient phrase 12 mg"
    result = score_candidate(source, source)
    serialized = str(result.breakdown)
    assert source not in serialized
