"""WP0 acceptance tests for the literature-ranking evaluation baseline."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.modules.evaluation.literature_ranking import (
    LiteratureRankingCase,
    evaluate_ranking,
    load_literature_ranking_jsonl,
)


def _case() -> LiteratureRankingCase:
    return LiteratureRankingCase(
        case_id="synthetic-wp0-001",
        result_fixture_id="synthetic-results-001",
        research_intent={"framework": "PICO", "question": "synthetic only"},
        relevance_labels_by_pmid={"pmid-1": 3, "pmid-2": 1, "pmid-3": -1},
        eligibility_labels_by_pmid={
            "pmid-1": "eligible",
            "pmid-2": "eligible",
            "pmid-3": "excluded",
        },
        dimension_labels_by_pmid={
            "pmid-1": {"population": 3, "intervention": 3, "outcome": 2},
            "pmid-2": {"population": 1},
        },
        required_pmids=["pmid-1"],
        forbidden_pmids=["pmid-3"],
        notes="Synthetic fixture; not a medical gold standard.",
        label_source="synthetic_fixture",
    )


def test_wp0_ranking_baseline_is_deterministic() -> None:
    case = _case()

    first = evaluate_ranking(
        case, ["pmid-1", "pmid-2", "pmid-3"], predicted_excluded_pmids=["pmid-3"]
    )
    second = evaluate_ranking(
        case, ["pmid-1", "pmid-2", "pmid-3"], predicted_excluded_pmids=["pmid-3"]
    )

    assert first == second
    assert first.ndcg_at_10 == pytest.approx(1.0)
    assert first.ndcg_at_20 == pytest.approx(1.0)
    assert first.mrr == pytest.approx(1.0)
    assert first.recall_at_50 == pytest.approx(1.0)
    assert first.precision_at_10 == pytest.approx(2 / 3)
    assert first.exclusion_precision == pytest.approx(1.0)


def test_wp0_validation_error_identifies_case_and_field(tmp_path: Path) -> None:
    invalid_case = _case().model_dump(mode="json")
    invalid_case["relevance_labels_by_pmid"] = {"pmid-1": 9}
    path = tmp_path / "invalid.jsonl"
    path.write_text(json.dumps(invalid_case), encoding="utf-8")

    with pytest.raises(ValueError, match=r"case_id='synthetic-wp0-001'.*relevance_labels_by_pmid"):
        load_literature_ranking_jsonl(path)


def test_wp0_contract_keeps_relevance_eligibility_and_dimensions_separate() -> None:
    case = _case()

    assert case.relevance_labels_by_pmid["pmid-1"] == 3
    assert case.eligibility_labels_by_pmid["pmid-3"] == "excluded"
    assert case.dimension_labels_by_pmid["pmid-1"]["intervention"] == 3


def test_wp0_minimal_fixture_is_explicitly_synthetic() -> None:
    fixture_path = Path("tests/fixtures/literature_ranking_minimal_synthetic.jsonl")

    cases = load_literature_ranking_jsonl(fixture_path)

    assert len(cases) == 1
    assert cases[0].label_source == "synthetic_fixture"


def test_wp0_baseline_declares_legacy_classic_and_unvalidated_status() -> None:
    report = evaluate_ranking(_case(), ["pmid-1", "pmid-2", "pmid-3"])

    assert report.classic_baseline_status == "legacy_proxy"
    assert report.medical_effect_status == "not_validated_without_expert_gold_standard"


def test_wp0_contract_has_no_commercial_metric_fields() -> None:
    keys = set(_case().model_dump())

    assert not keys.intersection({"jcr", "jif", "jci", "wos", "scopus", "impact_factor"})
