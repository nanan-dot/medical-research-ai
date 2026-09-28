"""P0 acceptance checks for trustworthy conditions, budgets, and traces."""

import json
from datetime import date
from pathlib import Path

from app.modules.document.parsers.schemas import ParsedDocument
from app.modules.document_navigation.budget import resolve_navigation_budget
from app.modules.document_navigation.conditions import (
    match_navigation_conditions,
    requested_navigation_conditions,
)
from app.modules.document_navigation.schema import (
    ConditionMatchStatus,
    NavigationStrategy,
)
from app.modules.document_navigation.service import _effective_budget_for_strategy
from tests.modules.document_navigation.test_api import navigation_client  # noqa: F401


def parsed_document(*, text: str, metadata: dict[str, object] | None = None) -> ParsedDocument:
    return ParsedDocument(
        source_path="study.pdf",
        title="Study",
        text=text,
        yaml_metadata=metadata or {},
    )


def test_reference_year_does_not_satisfy_publication_period() -> None:
    requested = requested_navigation_conditions("近三年 肺癌", today=date(2026, 9, 19))
    parsed = parsed_document(text="参考文献：Smith et al. 2025。")

    matches = match_navigation_conditions(requested, parsed, parsed.text)

    assert matches[0].status == ConditionMatchStatus.NOT_ASSESSED
    assert matches[0].source_field is None


def test_negated_rct_text_is_only_a_text_mention() -> None:
    requested = requested_navigation_conditions("随机对照试验", today=date(2026, 9, 19))
    parsed = parsed_document(text="本研究不是 RCT，而是回顾性队列研究。")

    matches = match_navigation_conditions(requested, parsed, parsed.text)

    assert matches[0].status == ConditionMatchStatus.TEXT_MENTION
    assert matches[0].basis == "text"
    assert matches[0].source_field is None


def test_structured_metadata_can_match_or_mismatch_conditions() -> None:
    requested = requested_navigation_conditions(
        "近三年 随机对照试验", today=date(2026, 9, 19)
    )
    parsed = parsed_document(
        text="研究摘要。",
        metadata={"publication_year": 2022, "study_design": "randomized controlled trial"},
    )

    matches = match_navigation_conditions(requested, parsed, parsed.text)

    assert [item.status for item in matches] == [
        ConditionMatchStatus.METADATA_MISMATCH,
        ConditionMatchStatus.METADATA_MATCH,
    ]
    assert [item.source_field for item in matches] == ["publication_year", "study_design"]


def test_negated_rct_metadata_is_a_mismatch() -> None:
    requested = requested_navigation_conditions("RCT", today=date(2026, 9, 19))
    parsed = parsed_document(
        text="研究摘要。", metadata={"study_design": "non-randomized controlled trial"}
    )

    matches = match_navigation_conditions(requested, parsed, parsed.text)

    assert matches[0].status == ConditionMatchStatus.METADATA_MISMATCH


def test_navigation_budget_never_exceeds_configured_caps() -> None:
    budget = resolve_navigation_budget(
        requested_limit=10,
        available_chunks=100,
        dense_top_k=6,
        sparse_top_k=7,
        fusion_top_k=8,
        rerank_candidate_top_k=5,
    )

    assert budget.candidate_limit == 5
    assert budget.final_limit == 5
    assert budget.status == "limited"
    assert budget.dense_top_k == 6
    assert budget.sparse_top_k == 7


def test_bm25_effective_budget_reports_sparse_stage_cap() -> None:
    budget = resolve_navigation_budget(
        requested_limit=10,
        available_chunks=100,
        dense_top_k=30,
        sparse_top_k=3,
        fusion_top_k=2,
        rerank_candidate_top_k=40,
    )

    effective = _effective_budget_for_strategy(
        budget,
        NavigationStrategy.BM25,
        available_chunks=100,
    )

    assert effective.candidate_limit == 3
    assert effective.final_limit == 3
    assert effective.status == "limited"


def test_navigation_reports_structured_condition_matches(navigation_client) -> None:  # noqa: F811
    client, _, _ = navigation_client
    response = client.post(
        "/api/v1/document-navigation/search",
        json={"query": "近三年 随机对照试验 PD-1"},
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert {item["status"] for item in result["condition_status"]} == {"unverified"}
    assert {item["status"] for item in result["condition_matches"]} == {"not_assessed"}
    assert response.json()["effective_indexed_only"] is True


def test_navigation_trace_is_minimized_by_default(
    navigation_client, monkeypatch, tmp_path: Path  # noqa: F811
) -> None:
    from app.modules.document_navigation import service

    trace_directory = tmp_path / "trace-data"
    monkeypatch.setattr(service.settings, "RAG_TRACE_ENABLED", True)
    monkeypatch.setattr(service.settings, "RAG_TRACE_DIR", trace_directory)
    monkeypatch.setattr(service.settings, "RAG_TRACE_STORE_QUERY", False)
    monkeypatch.setattr(service.settings, "RAG_TRACE_STORE_TEXT", False)
    client, _, _ = navigation_client

    payload = client.post(
        "/api/v1/document-navigation/search", json={"query": "PD-1"}
    ).json()

    assert payload["trace_id"]
    trace_files = list((trace_directory / "rag_traces").glob("*.jsonl"))
    stored = json.loads(trace_files[0].read_text(encoding="utf-8").splitlines()[0])
    assert stored["trace_id"] == payload["trace_id"]
    assert stored["query_original"] is None
    assert stored["query_plan"]["query"] == "[not_persisted]"
    assert all(not item["text_original"] for item in stored["selected_evidence"]["evidence"])
    assert all("/" not in item["source_path"] for item in stored["selected_evidence"]["evidence"])
