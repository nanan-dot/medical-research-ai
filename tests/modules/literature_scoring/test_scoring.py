"""Acceptance coverage for scoring data semantics independent of providers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.modules.literature_scoring.schema import ScoringRunCreate
from app.modules.literature_scoring.scoring import (
    METRIC_AVAILABLE,
    METRIC_HISTORY,
    MetricValue,
    popularity_from_yearly_counts,
    weighted_score,
)
from app.modules.literature_scoring.service import LiteratureScoringService
from app.modules.literature_search.service import LiteratureSearchService


def test_missing_metric_is_not_represented_as_zero() -> None:
    result = weighted_score(
        [
            (0.7, MetricValue(86, METRIC_AVAILABLE)),
            (0.3, MetricValue(None, "provider_unavailable")),
        ]
    )
    assert result.score == 86
    assert result.status == METRIC_AVAILABLE


def test_cumulative_or_short_history_cannot_claim_popularity() -> None:
    result = popularity_from_yearly_counts({2025: 12}, 2025)
    assert result.score is None
    assert result.status == METRIC_HISTORY


@pytest.mark.asyncio
async def test_force_refresh_uses_a_distinct_generation_fingerprint() -> None:
    service = LiteratureScoringService(None)  # type: ignore[arg-type]
    service.results = SimpleNamespace(
        get_result=AsyncMock(return_value=SimpleNamespace(items_json="[]"))
    )
    intent = SimpleNamespace(id=8, dimensions_json="{}")
    created = []

    async def create(generation):
        generation.id = len(created) + 1
        created.append(generation)
        return generation

    service.generations = SimpleNamespace(
        get_confirmed_intent=AsyncMock(return_value=intent),
        get_generation_by_fingerprint=AsyncMock(return_value=None),
        create=create,
        add_scores=AsyncMock(),
    )
    await service.create_run(
        4, ScoringRunCreate(intent_snapshot_id=8, force_refresh=True)
    )
    await service.create_run(
        4, ScoringRunCreate(intent_snapshot_id=8, force_refresh=True)
    )
    assert len(created) == 2
    assert created[0].input_fingerprint != created[1].input_fingerprint


@pytest.mark.asyncio
async def test_queue_run_persists_options_without_running_provider_work() -> None:
    service = LiteratureScoringService(None)  # type: ignore[arg-type]
    service.results = SimpleNamespace(
        get_result=AsyncMock(return_value=SimpleNamespace(items_json="[]"))
    )
    intent = SimpleNamespace(id=8)

    async def create(generation):
        generation.id = 12
        return generation

    service.generations = SimpleNamespace(
        get_confirmed_intent=AsyncMock(return_value=intent),
        get_generation_by_fingerprint=AsyncMock(return_value=None),
        create=create,
    )
    run = await service.queue_run(
        4, ScoringRunCreate(intent_snapshot_id=8, include_external_metrics=True)
    )
    assert run.status == "queued"
    assert run.generation_id == 12


@pytest.mark.asyncio
async def test_cancel_run_persists_terminal_state_before_scheduler_interrupt() -> None:
    service = LiteratureScoringService(None)  # type: ignore[arg-type]
    generation = SimpleNamespace(
        id=12,
        algorithm_version="ranking-v3.0",
        cancel_requested=False,
        status="scoring",
        last_error=None,
        finished_at=None,
    )
    service.generations = SimpleNamespace(
        get_building_generation=AsyncMock(return_value=generation)
    )
    run = await service.cancel_run(4)
    assert run.status == "failed"
    assert generation.cancel_requested is True
    assert generation.last_error == "cancelled_by_user"


def test_zero_score_remains_distinct_from_missing_score() -> None:
    score = SimpleNamespace(relevance_score=0.0)
    assert LiteratureSearchService._score_sort_value(score, "relevance_score") == 0.0
    assert LiteratureSearchService._score_sort_value(None, "relevance_score") == -1.0


def test_openalex_metrics_can_be_explicitly_requested() -> None:
    request = ScoringRunCreate(intent_snapshot_id=8, include_external_metrics=True)
    assert request.include_external_metrics is True


def test_status_marks_missing_openalex_data_as_not_collected_not_zero() -> None:
    signals = LiteratureScoringService._status_signals(
        SimpleNamespace(),
        {
            "1": SimpleNamespace(
                cited_by_count=None,
                popularity_score=None,
                classic_score=None,
                citation_metrics_json='{"status":"not_collected"}',
            )
        },
    )
    assert signals["article_impact"] == "not_collected"
    assert signals["popularity"] == "not_collected"


def test_sort_capabilities_do_not_claim_openalex_sort_without_article_data() -> None:
    capabilities = LiteratureSearchService._sort_capabilities(
        SimpleNamespace(),
        {
            "1": SimpleNamespace(
                popularity_score=None, article_impact_score=None, classic_score=None
            )
        },
    )
    assert capabilities["popular"].available is False
    assert capabilities["article_impact"].available is False
    assert capabilities["recommended"].available is True


@pytest.mark.asyncio
async def test_latest_failed_generation_is_reported_while_old_active_scores_remain() -> (
    None
):
    service = LiteratureScoringService(None)  # type: ignore[arg-type]
    active = SimpleNamespace(id=4, status="active")
    failed = SimpleNamespace(
        id=5,
        status="failed",
        completed_count=0,
        expected_count=2,
        started_at=None,
        finished_at=None,
        created_at=None,
        algorithm_version="ranking-v3.0",
        last_error="cancelled_by_user",
    )
    service.results = SimpleNamespace(
        get_result=AsyncMock(return_value=SimpleNamespace(items_json="[]"))
    )
    service.generations = SimpleNamespace(
        get_active_generation=AsyncMock(return_value=active),
        get_building_generation=AsyncMock(return_value=None),
        get_latest_generation=AsyncMock(return_value=failed),
        get_active_scores=AsyncMock(return_value={}),
    )
    status = await service.get_status(4)
    assert status.status == "failed"
    assert status.active_generation_id == 4
    assert status.last_error == "cancelled_by_user"
