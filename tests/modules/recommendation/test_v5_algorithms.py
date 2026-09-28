"""Acceptance tests for deterministic V5 recommendation facts."""

from app.modules.literature_search.schema import CitationItem
from app.modules.recommendation.overlap import classify_overlap, normalize_doi
from app.modules.recommendation.relevance import score_relevance
from app.modules.recommendation.scoring import (
    MODE_WEIGHTS,
    evidence_fit,
    intent_concept_coverage,
    openalex_signal,
    priority_score,
    select_ranked_novel_pmids,
    stable_rank,
    weighted_available_score,
)
from app.modules.recommendation.v5_query import (
    build_intent_query,
    build_intent_query_variants,
)
from app.modules.recommendation.v5_service import input_fingerprint


def test_missing_components_are_not_zero_and_are_renormalized() -> None:
    score, used = weighted_available_score(
        {"relevance": 0.8, "incremental": None}, {"relevance": 0.6, "incremental": 0.4}
    )
    assert score == 0.8
    assert used == ["relevance"]
    assert weighted_available_score({"relevance": None}, {"relevance": 1}) == (None, [])


def test_mode_weights_are_versioned_contract() -> None:
    assert MODE_WEIGHTS["balanced"] == {
        "relevance": 0.60,
        "incremental": 0.25,
        "evidence_fit": 0.15,
    }
    assert "recency" in MODE_WEIGHTS["latest"]
    assert (
        MODE_WEIGHTS["key_evidence"]["evidence_fit"]
        > MODE_WEIGHTS["balanced"]["evidence_fit"]
    )
    assert priority_score(
        "latest", relevance=0.1, incremental=1, evidence_fit=1, recency=1
    ) == (None, ["below_minimum_relevance"])


def test_evidence_fit_rule_matrix_preserves_unknown_as_null() -> None:
    assert evidence_fit("treatment", ["Randomized Controlled Trial"])[0] == 1
    assert evidence_fit("prognosis", ["Prospective Cohort"])[0] == 1
    assert evidence_fit(None, ["Review"]) == (None, [])
    assert evidence_fit("diagnosis", []) == (None, [])


def test_overlap_preserves_all_hits_with_explicit_priority() -> None:
    result = classify_overlap(
        pmid="1",
        doi="https://doi.org/10.1/X",
        source_pmids={"1"},
        source_dois=set(),
        reading_pmids={"1"},
        library_pmids=set(),
        library_dois={"10.1/x"},
        knowledge_pmids=set(),
        knowledge_dois=set(),
    )
    assert result.status == "in_source_result"
    assert {item["collection"] for item in result.evidence} == {
        "in_source_result",
        "in_reading_plan",
        "in_library",
    }
    assert normalize_doi("DOI: 10.1/X") == "10.1/x"


def test_conservative_existing_title_normalizer_marks_near_duplicate() -> None:
    result = classify_overlap(
        pmid="new",
        doi=None,
        title="A Trial: Of Cancer.",
        covered_titles={"a trial of cancer"},
        source_pmids=set(),
        source_dois=set(),
        reading_pmids=set(),
        library_pmids=set(),
        library_dois=set(),
        knowledge_pmids=set(),
        knowledge_dois=set(),
    )
    assert result.status == "near_duplicate"
    assert result.limitations == []


def test_intent_query_is_auditable_and_excludes_retractions() -> None:
    built = build_intent_query(
        {"disease": ["gastric cancer"], "mesh": ["Stomach Neoplasms"]}
    )
    assert '"gastric cancer"[Title/Abstract]' in built.query
    assert '"Stomach Neoplasms"[MeSH Terms]' in built.query
    assert "NOT retracted publication[pt]" in built.query
    assert {term.source for term in built.terms} == {"intent_snapshot"}


def test_intent_query_variants_relax_secondary_dimensions_before_core_terms() -> None:
    variants = build_intent_query_variants(
        {"disease": ["interstitial lung disease"], "intervention": ["antifibrotic"], "outcome": ["safety"]}
    )
    assert len(variants) == 2
    assert '"safety"[Title/Abstract]' in variants[0].query
    assert '"safety"[Title/Abstract]' not in variants[1].query
    assert '"interstitial lung disease"[Title/Abstract]' in variants[1].query
    assert '"antifibrotic"[Title/Abstract]' in variants[1].query


def test_stable_rank_and_algorithm_fingerprint() -> None:
    assert stable_rank([("2", 0.8, 2024), ("1", 0.8, 2024), ("3", None, 2025)]) == [
        "1",
        "2",
        "3",
    ]
    common = {
        "research_context_id": 1,
        "intent_fingerprint": "i",
        "result_id": 2,
        "result_snapshot": "[]",
        "mode": "balanced",
        "candidate_count": 10,
    }
    assert input_fingerprint(**common, algorithm_version="v1") != input_fingerprint(
        **common, algorithm_version="v2"
    )


def test_incremental_baseline_comes_from_source_snapshot_metadata() -> None:
    item = CitationItem(
        pmid="1",
        title="Adults receiving treatment A",
        abstract="Mortality outcome",
        publication_types=["Randomized Controlled Trial"],
    )
    baseline = intent_concept_coverage(
        [item],
        {"population": ["Adults"], "outcome": ["mortality", "quality of life"]},
    )
    assert baseline["population"]["Adults"] == 1
    assert baseline["outcome"]["quality of life"] == 0


def test_openalex_is_optional_bounded_signal() -> None:
    assert openalex_signal(None) is None
    assert openalex_signal(0) == 0
    signal = openalex_signal(10)
    assert signal is not None and 0 < signal < 1


def test_relevance_renormalizes_missing_pubmed_fields() -> None:
    title_only = CitationItem(pmid="1", title="gastric cancer")
    score, matches, sources = score_relevance(
        title_only, {"disease": ["gastric cancer"]}
    )
    assert score == 1
    assert matches[0]["field"] == "pubmed_title"
    assert sources == ["pubmed_title"]


def test_novel_selection_filters_below_threshold_then_sorts_before_limit() -> None:
    selected = select_ranked_novel_pmids(
        [
            ("low", None, 2026),
            ("medium", 0.6, 2026),
            ("high", 0.9, 2024),
        ],
        candidate_count=1,
    )
    assert selected == ["high"]
