"""期刊指标导入、生命周期、动态装配与性能的直接 AC 验收。"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.literature_search.journal_metric_repository import (
    JournalMetricRepository,
)
from app.modules.literature_search.model import (
    JournalMetricImportBatch,
    LiteratureCommercialJournalMetric,
    LiteratureSearchResult,
)
from app.modules.literature_search.schema import CitationItem

CSV_HEADER = "journal_name,issn,metric_year,impact_factor,impact_factor_year,jcr_best_quartile,jcr_year,wos_indexes,wos_year,cas_quartile,cas_year\n"


class _Executor:
    def __init__(self, count: int = 1) -> None:
        self.count = count
        self.calls: list[str] = []

    async def execute(self, query: str, *, retmax: int = 20):
        self.calls.append(query)
        return [
            CitationItem(
                pmid=str(index + 1),
                title=f"Paper {index}",
                journal="Example Journal",
                issn="2049-3630",
                year=2014 + index % 10,
                verified=True,
            )
            for index in range(self.count)
        ], self.count


@pytest.fixture
async def metric_api(tmp_path: Path, monkeypatch):
    from app.modules.literature_search.service import LiteratureSearchService

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'metrics.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    executor = _Executor()
    original_init = LiteratureSearchService.__init__

    def patched_init(self, session, **kwargs):
        original_init(self, session, pubmed_executor=executor)

    monkeypatch.setattr(LiteratureSearchService, "__init__", patched_init)
    app.dependency_overrides[get_session] = override_session
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, factory, executor
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def _csv(year: int, impact: str = "1.2", *, cas_year: int | None = None) -> bytes:
    cas = cas_year or year
    return (
        CSV_HEADER
        + f"Example Journal,2049-3630,{year},{impact},{year},Q1,{year},ESCI,{year},1区,{cas}\n"
    ).encode()


def _preview(client: TestClient, content: bytes) -> str:
    response = client.post(
        "/api/v1/journal-metrics/imports/preview",
        files={"file": ("metrics.csv", content, "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()["file_hash"]


def _commit(
    client: TestClient, content: bytes, year: int, version: str
) -> dict[str, object]:
    digest = _preview(client, content)
    response = client.post(
        "/api/v1/journal-metrics/imports/commit",
        files={"file": (f"metrics-{version}.csv", content, "text/csv")},
        data={
            "expected_file_hash": digest,
            "provider": "Example Provider",
            "provider_version": version,
            "edition_year": str(year),
            "license_provenance": "licensed test fixture",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.asyncio
async def test_preview_is_read_only_api(metric_api) -> None:
    client, factory, _ = metric_api
    _preview(client, _csv(2025))
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(JournalMetricImportBatch)
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count()).select_from(LiteratureCommercialJournalMetric)
            )
            == 0
        )


@pytest.mark.asyncio
async def test_preview_blocking_errors_are_stable(metric_api) -> None:
    client, factory, _ = metric_api
    response = client.post(
        "/api/v1/journal-metrics/imports/preview",
        files={"file": ("bad.csv", b"name\nX\n", "text/csv")},
    )
    assert (
        response.status_code == 422
        and response.json()["error"]["code"] == "journal_metric_missing_headers"
    )
    encoding = client.post(
        "/api/v1/journal-metrics/imports/preview",
        files={"file": ("bad.csv", b"journal_name,metric_year\n\xff,2025\n", "text/csv")},
    )
    assert encoding.status_code == 422
    assert encoding.json()["error"]["code"] == "journal_metric_invalid_encoding"
    invalid = client.post(
        "/api/v1/journal-metrics/imports/preview",
        files={"file": ("bad.csv", b"journal_name,metric_year,impact_factor\nExample Journal,2025,-1\n", "text/csv")},
    )
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "journal_metric_invalid_rows"
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(JournalMetricImportBatch)
            )
            == 0
        )


@pytest.mark.asyncio
async def test_commit_rolls_back_batch_and_metrics(metric_api, monkeypatch) -> None:
    client, factory, _ = metric_api
    content = _csv(2025)
    digest = _preview(client, content)
    original = JournalMetricRepository.add_batch

    async def fail_after_flush(self, batch, metrics):
        await original(self, batch, metrics)
        raise RuntimeError("forced transactional failure")

    monkeypatch.setattr(JournalMetricRepository, "add_batch", fail_after_flush)
    response = client.post(
        "/api/v1/journal-metrics/imports/commit",
        files={"file": ("metrics.csv", content, "text/csv")},
        data={
            "expected_file_hash": digest,
            "provider": "Example",
            "provider_version": "v1",
            "edition_year": "2025",
            "license_provenance": "licensed",
        },
    )
    assert response.status_code == 500
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(JournalMetricImportBatch)
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count()).select_from(LiteratureCommercialJournalMetric)
            )
            == 0
        )


@pytest.mark.asyncio
async def test_commit_hash_mismatch_writes_nothing(metric_api) -> None:
    client, factory, _ = metric_api
    response = client.post(
        "/api/v1/journal-metrics/imports/commit",
        files={"file": ("metrics.csv", _csv(2025), "text/csv")},
        data={
            "expected_file_hash": "0" * 64,
            "provider": "Example",
            "provider_version": "v1",
            "edition_year": "2025",
            "license_provenance": "licensed",
        },
    )
    assert (
        response.status_code == 422
        and response.json()["error"]["code"] == "journal_metric_preview_mismatch"
    )
    async with factory() as session:
        assert (
            await session.scalar(
                select(func.count()).select_from(JournalMetricImportBatch)
            )
            == 0
        )


def test_duplicate_file_rejected(metric_api) -> None:
    client, _, _ = metric_api
    content = _csv(2025)
    _commit(client, content, 2025, "v1")
    digest = _preview(client, content)
    response = client.post(
        "/api/v1/journal-metrics/imports/commit",
        files={"file": ("again.csv", content, "text/csv")},
        data={
            "expected_file_hash": digest,
            "provider": "Other",
            "provider_version": "v2",
            "edition_year": "2025",
            "license_provenance": "licensed",
        },
    )
    assert (
        response.status_code == 422
        and response.json()["error"]["code"] == "journal_metric_duplicate_import"
    )


def test_activate_switches_same_provider_year_version(metric_api) -> None:
    client, _, _ = metric_api
    old = _commit(client, _csv(2025, "1.2"), 2025, "v1")
    new = _commit(client, _csv(2025, "2.4"), 2025, "v2")
    assert (
        client.post(f"/api/v1/journal-metrics/imports/{old['id']}/activate").status_code
        == 200
    )
    assert (
        client.post(f"/api/v1/journal-metrics/imports/{new['id']}/activate").status_code
        == 200
    )
    batches = client.get("/api/v1/journal-metrics/imports").json()["items"]
    active = [batch for batch in batches if batch["is_active"]]
    assert len(active) == 1 and active[0]["id"] == new["id"]
    result_id = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    ).json()["id"]
    summary = client.get(f"/api/v1/literature-search/{result_id}/results").json()[
        "items"
    ][0]["journal_metric"]
    assert summary["latest"]["impact_factor"]["value"] == 2.4


def test_disjoint_range_returns_422_without_pubmed_call(metric_api) -> None:
    client, _, executor = metric_api
    response = client.post(
        "/api/v1/literature-search/execute",
        json={
            "boolean_query": "cancer",
            "date_range": {"start_year": 1990, "end_year": 2000},
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "literature_search_range_outside_policy"
    assert executor.calls == []


def test_default_execute_query_contains_rolling_window(metric_api) -> None:
    client, _, executor = metric_api
    response = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    )
    assert response.status_code == 200
    assert '"2012"[Date - Publication]' in executor.calls[0]
    assert '"2026"[Date - Publication]' in executor.calls[0]


def test_result_page_not_configured_degrades_cleanly(metric_api) -> None:
    client, _, _ = metric_api
    result_id = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    ).json()["id"]
    payload = client.get(f"/api/v1/literature-search/{result_id}/results").json()
    assert payload["items"][0]["journal_metric"] == {
        "status": "not_configured",
        "match_method": None,
        "latest": None,
        "reason": "no_active_journal_metric_import",
    }


@pytest.mark.asyncio
async def test_legacy_snapshot_result_bibtex_filter_compatible(metric_api) -> None:
    client, factory, _ = metric_api
    async with factory() as session:
        entity = LiteratureSearchResult(
            query="legacy",
            total_count=1,
            items_json='[{"pmid":"42","title":"Legacy paper","authors":["Li A"],"journal":"Example Journal","year":2020}]',
        )
        session.add(entity)
        await session.commit()
        result_id = entity.id
    page = client.get(f"/api/v1/literature-search/{result_id}/results?year_from=2020")
    bibtex = client.get(f"/api/v1/literature-search/{result_id}/bibtex")
    assert page.status_code == 200 and page.json()["items"][0]["item"]["issn"] is None
    assert bibtex.status_code == 200 and "Legacy paper" in bibtex.text


def test_publication_year_requires_exact_year_and_detail_has_ten(metric_api) -> None:
    client, _, _ = metric_api
    for year in range(2015, 2026):
        batch = _commit(client, _csv(year, str(year / 1000)), year, f"v{year}")
        client.post(f"/api/v1/journal-metrics/imports/{batch['id']}/activate")
    result_id = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    ).json()["id"]
    detail = client.get(
        f"/api/v1/literature-search/{result_id}/items/1/journal-metrics"
    ).json()
    assert detail["publication_year_metric"] is None
    assert detail["publication_year_reason"] == "publication_year_metric_not_available"
    assert [row["metric_year"] for row in detail["history"]] == list(
        range(2025, 2015, -1)
    )


def test_missing_if_serializes_null_and_esci_is_not_promoted(metric_api) -> None:
    client, _, _ = metric_api
    content = _csv(2025, "")
    batch = _commit(client, content, 2025, "v1")
    client.post(f"/api/v1/journal-metrics/imports/{batch['id']}/activate")
    result_id = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    ).json()["id"]
    summary = client.get(f"/api/v1/literature-search/{result_id}/results").json()[
        "items"
    ][0]["journal_metric"]
    assert summary["latest"]["impact_factor"]["value"] is None
    assert summary["latest"]["wos"]["indexes"] == ["ESCI"]


def test_detail_rejects_pmid_outside_result(metric_api) -> None:
    client, _, _ = metric_api
    result_id = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    ).json()["id"]
    assert (
        client.get(
            f"/api/v1/literature-search/{result_id}/items/999/journal-metrics"
        ).status_code
        == 404
    )


def test_archive_active_batch_does_not_reactivate_old(metric_api) -> None:
    client, _, _ = metric_api
    old = _commit(client, _csv(2025, "1.0"), 2025, "v1")
    new = _commit(client, _csv(2025, "2.0"), 2025, "v2")
    client.post(f"/api/v1/journal-metrics/imports/{old['id']}/activate")
    client.post(f"/api/v1/journal-metrics/imports/{new['id']}/activate")
    client.post(f"/api/v1/journal-metrics/imports/{new['id']}/archive")
    assert not any(
        batch["is_active"]
        for batch in client.get("/api/v1/journal-metrics/imports").json()["items"]
    )


def test_eleventh_active_year_is_archived_not_deleted(metric_api) -> None:
    client, _, _ = metric_api
    ids = []
    for year in range(2015, 2026):
        batch = _commit(client, _csv(year), year, f"v{year}")
        ids.append(batch["id"])
        client.post(f"/api/v1/journal-metrics/imports/{batch['id']}/activate")
    batches = client.get("/api/v1/journal-metrics/imports?limit=100").json()["items"]
    assert len(batches) == 11
    oldest = next(batch for batch in batches if batch["id"] == ids[0])
    assert oldest["status"] == "archived" and not oldest["is_active"]


def test_metric_import_does_not_change_score_or_order(metric_api) -> None:
    client, _, _ = metric_api
    result_id = client.post(
        "/api/v1/literature-search/execute", json={"boolean_query": "cancer"}
    ).json()["id"]
    before = client.get(f"/api/v1/literature-search/{result_id}/results").json()
    batch = _commit(client, _csv(2025), 2025, "v1")
    client.post(f"/api/v1/journal-metrics/imports/{batch['id']}/activate")
    after = client.get(f"/api/v1/literature-search/{result_id}/results").json()
    assert [row["item"]["pmid"] for row in before["items"]] == [
        row["item"]["pmid"] for row in after["items"]
    ]
    assert [row["score_summary"] for row in before["items"]] == [
        row["score_summary"] for row in after["items"]
    ]


def test_hundred_item_page_uses_constant_metric_queries(
    metric_api, monkeypatch
) -> None:
    client, _, executor = metric_api
    executor.count = 100
    batch = _commit(client, _csv(2025), 2025, "v1")
    client.post(f"/api/v1/journal-metrics/imports/{batch['id']}/activate")
    calls = 0
    original = JournalMetricRepository.candidates

    async def counted(self, issns, names):
        nonlocal calls
        calls += 1
        return await original(self, issns, names)

    monkeypatch.setattr(JournalMetricRepository, "candidates", counted)
    result_id = client.post(
        "/api/v1/literature-search/execute",
        json={"boolean_query": "cancer", "retmax": 100},
    ).json()["id"]
    response = client.get(
        f"/api/v1/literature-search/{result_id}/results?page_size=100"
    )
    assert response.status_code == 200 and len(response.json()["items"]) == 100
    assert calls == 1
