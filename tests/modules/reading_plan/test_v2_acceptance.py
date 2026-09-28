"""AC-RPB-01..12 behavioral coverage for reading-plan V2."""

import asyncio
import json

import pytest
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError
from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.literature_search.model import LiteratureSearchResult
from app.modules.reading_plan.model import ReadingPlan, ReadingPlanItem
from app.modules.reading_plan.reason import build_reading_reason
from app.modules.reading_plan.schema import (
    ManualItemCreate,
    PlanGenerateRequest,
    PlanItemPatch,
    PromoteCoreRequest,
)
from app.modules.reading_plan.service import ReadingPlanService


@pytest.fixture
async def session(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'v2.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    rows = [{"pmid": str(80_000_000 + index), "title": f"Paper {index}", "authors": ["Author"], "year": 2024, "has_abstract": True, "publication_types": [kind]} for index, kind in enumerate(["Systematic Review", "Practice Guideline", "Randomized Controlled Trial", "Journal Article"] * 6)]
    async with factory() as setup:
        setup.add(LiteratureSearchResult(query="q", total_count=len(rows), items_json=json.dumps(rows)))
        await setup.commit()
    async with factory() as active:
        yield active
    await engine.dispose()


@pytest.mark.asyncio
async def test_ac_rpb_01_02_03_reason_is_chinese_honest_and_persisted(session: AsyncSession) -> None:
    result = await session.get(LiteratureSearchResult, 1)
    rows = json.loads(result.items_json)
    rows[0].update({"title": "IPF treatment trial", "abstract": "IPF treatment outcome", "mesh_terms": ["Pulmonary Fibrosis"], "publication_types": ["Randomized Controlled Trial"]})
    result.items_json = json.dumps(rows)
    plan = await ReadingPlanService(session).generate(1, PlanGenerateRequest())
    first = next(item for stage in plan.stages for item in stage.core)
    assert first.reading_reason.stage_fit and first.reading_reason.incremental_value
    assert first.reading_reason.generation_method == "deterministic"
    assert first.reading_reason.status == "partial"
    original = first.reading_reason.model_dump()
    reread = await ReadingPlanService(session).get(1, plan.id)
    assert next(item for stage in reread.stages for item in stage.core if item.pmid == first.pmid).reading_reason.model_dump() == original


@pytest.mark.asyncio
async def test_ac_rpb_04_volume_issue_pages_and_null_mapping(session: AsyncSession) -> None:
    result = await session.get(LiteratureSearchResult, 1)
    rows = json.loads(result.items_json)
    rows[0].update({"volume": "12", "issue": "3", "pages": "100-110", "doi": "10.1/example"})
    result.items_json = json.dumps(rows)
    plan = await ReadingPlanService(session).generate(1, PlanGenerateRequest())
    cards = [item for stage in plan.stages for item in stage.core]
    card = next(item for item in cards if item.pmid == rows[0]["pmid"])
    assert (card.volume, card.issue, card.pages, card.doi) == ("12", "3", "100-110", "10.1/example")


@pytest.mark.asyncio
async def test_ac_rpb_05_06_08_versions_failure_and_preserve(session: AsyncSession, monkeypatch) -> None:
    service = ReadingPlanService(session)
    first = await service.generate(1, PlanGenerateRequest())
    previous = await service.repo.plan(first.id)
    previous.items[0].is_locked = True
    await session.commit()
    async def fail(_result_id: int) -> None: raise RuntimeError("activation failed")
    monkeypatch.setattr(service.repo, "archive_active", fail)
    with pytest.raises(RuntimeError): await service.generate(1, PlanGenerateRequest())
    await session.rollback()
    assert (await service.active(1)).id == first.id
    monkeypatch.undo()
    second = await service.replan(1, first.id, PlanGenerateRequest(preserve=True))
    page = await service.list_versions(1, 20, 0)
    assert [item.version for item in page.items] == [2, 1]
    assert (await service.repo.plan(second.id)).items[0].is_locked


@pytest.mark.asyncio
async def test_ac_rpb_05_history_isolated_and_paginated(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    first = await service.generate(1, PlanGenerateRequest())
    await session.commit()
    await service.replan(1, first.id, PlanGenerateRequest())
    session.add(LiteratureSearchResult(query="other", total_count=0, items_json="[]"))
    await session.commit()
    assert [row.version for row in (await service.list_versions(1, 1, 1)).items] == [1]
    assert (await service.list_versions(2, 20, 0)).total == 0


@pytest.mark.asyncio
async def test_ac_rpb_07_two_independent_sessions_keep_active_unique(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'concurrent.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    rows = [{"pmid": str(90_000_000 + index), "title": str(index), "publication_types": ["Journal Article"]} for index in range(20)]
    async with factory() as setup:
        setup.add(LiteratureSearchResult(query="q", total_count=20, items_json=json.dumps(rows)))
        await setup.commit()

    async def create() -> int | str:
        async with factory() as isolated:
            try:
                plan = await ReadingPlanService(isolated).generate(1, PlanGenerateRequest())
                await isolated.commit()
                return plan.version
            except ConflictError:
                await isolated.rollback()
                return "conflict"

    outcomes = await asyncio.gather(create(), create())
    async with factory() as verify:
        plans = list((await verify.scalars(select(ReadingPlan).where(ReadingPlan.result_id == 1))).all())
    versions = [plan.version for plan in plans]
    assert len(versions) == len(set(versions))
    assert sum(plan.status == "active" for plan in plans) == 1
    assert all(value == "conflict" or isinstance(value, int) for value in outcomes)
    await engine.dispose()


@pytest.mark.asyncio
async def test_ac_rpb_09_candidate_pool_500_stable_pages(session: AsyncSession) -> None:
    result = await session.get(LiteratureSearchResult, 1)
    rows = [{"pmid": str(70_000_000 + index), "title": f"candidate {index}", "authors": ["Author"], "year": 2020 + index % 5, "publication_types": ["Journal Article"]} for index in range(500)]
    result.items_json = json.dumps(rows)
    result.total_count = 500
    service = ReadingPlanService(session)
    plan = await service.generate(1, PlanGenerateRequest())
    one = await service.candidates(1, plan.id, "frontier", 1, 20, None, None, None)
    last = await service.candidates(1, plan.id, "frontier", (one.total + 19) // 20, 20, None, None, None)
    empty = await service.candidates(1, plan.id, "frontier", 999, 20, None, None, None)
    assert one.total > 0 and one.items and last.items and empty.items == []
    repeated = await service.candidates(1, plan.id, "frontier", 1, 20, None, None, None)
    filtered = await service.candidates(
        1, plan.id, "frontier", 1, 20, "70000042", 2022, "Journal Article"
    )
    assert [item.pmid for item in repeated.items] == [item.pmid for item in one.items]
    assert filtered.total == 1
    assert filtered.items[0].title == "candidate 42"


@pytest.mark.asyncio
async def test_reason_tracks_stage_role_and_manual_provenance(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    created = await service.generate(1, PlanGenerateRequest())
    source_stage = next(stage for stage in created.stages if stage.core)
    target_stage = "frontier" if source_stage.stage != "frontier" else "overview"
    item = source_stage.core[0]

    moved = await service.patch_item(
        1,
        created.id,
        item.pmid,
        PlanItemPatch(stage=target_stage, role="candidate"),
    )
    assert all(item.pmid != value.pmid for stage in moved.stages for value in stage.core)
    page = await service.candidates(
        1, created.id, target_stage, 1, 100, item.pmid, None, None
    )
    moved_item = page.items[0]
    assert "候选" in moved_item.reading_reason.headline
    assert moved_item.reading_reason.stage_fit[0] != item.reading_reason.stage_fit[0]

    manual = await service.add_manual(
        1,
        created.id,
        ManualItemCreate(pmid=item.pmid, stage=target_stage, role="core"),
    )
    manual_item = next(
        value for stage in manual.stages for value in stage.core if value.pmid == item.pmid
    )
    assert manual_item.source == "manual"
    assert any("人工" in value for value in manual_item.reading_reason.limitations)

    demoted = await service.demote(1, created.id, target_stage, item.pmid)
    assert all(item.pmid != value.pmid for stage in demoted.stages for value in stage.core)
    demoted_page = await service.candidates(
        1, created.id, target_stage, 1, 100, item.pmid, None, None
    )
    assert "候选" in demoted_page.items[0].reading_reason.headline

    promoted = await service.promote(
        1,
        created.id,
        target_stage,
        PromoteCoreRequest(pmid=item.pmid),
    )
    promoted_item = next(
        value for stage in promoted.stages for value in stage.core if value.pmid == item.pmid
    )
    assert "优先" in promoted_item.reading_reason.headline


@pytest.mark.asyncio
async def test_non_lock_operational_error_is_not_mislabeled_as_conflict(
    session: AsyncSession, monkeypatch
) -> None:
    service = ReadingPlanService(session)

    async def fail(_result_id: int) -> None:
        raise OperationalError("select", {}, RuntimeError("no such table"))

    monkeypatch.setattr(service.repo, "archive_active", fail)
    with pytest.raises(OperationalError):
        await service.generate(1, PlanGenerateRequest())


@pytest.mark.asyncio
async def test_ac_rpb_10_metrics_are_not_fabricated(session: AsyncSession) -> None:
    plan = await ReadingPlanService(session).generate(1, PlanGenerateRequest())
    assert all(item.journal_metrics["status"] == "not_configured" for stage in plan.stages for item in stage.core)


def test_ac_rpb_11_12_contract_and_migration_are_declared() -> None:
    # Migration round-trip is executed by the release gate; model preserves the legacy string.
    assert "reading_reason_json" in ReadingPlanItem.__table__.c


def test_reason_matching_prefers_medical_terms_and_ignores_generic_words() -> None:
    from app.modules.literature_search.schema import CitationItem

    citation = CitationItem(
        pmid="1",
        title="进行性肺纤维化患者的 treatment study",
        abstract="肺纤维化疾病进展",
        publication_types=["Clinical Trial"],
    )
    reason = build_reading_reason(
        citation,
        stage="primary_evidence",
        role="core",
        intent={"population": "肺纤维化患者", "intervention": "treatment"},
        prior_stage_types=set(),
        has_score=False,
    )
    matches = "".join(reason["research_question_matches"])
    assert "肺纤维化" in matches
    assert "treatment" not in matches
