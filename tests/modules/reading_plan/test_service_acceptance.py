"""Direct service acceptance tests for persistence, batching, and protection."""

import json
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.exceptions import NotFoundError, UnprocessableEntityError
from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.literature_search.model import (
    JournalMetricImportBatch,
    LiteratureCommercialJournalMetric,
    LiteratureDuplicateGroup,
    LiteratureDuplicateGroupMember,
    LiteratureSearchItemState,
    LiteratureSearchResult,
)
from app.modules.literature_search.service import LiteratureSearchService
from app.modules.reading_plan.model import ReadingPlan
from app.modules.reading_plan.schema import (
    ManualItemCreate,
    PlanGenerateRequest,
    PromoteCoreRequest,
)
from app.modules.reading_plan.service import ReadingPlanService


@pytest.fixture
async def session(tmp_path) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'service.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    items = [
        {
            "pmid": str(60_000_000 + index),
            "title": f"Title {index}",
            "authors": [f"Author {index}"],
            "journal": "Metric Journal" if index == 20 else "Unconfigured",
            "issn": "1234-5678" if index == 20 else None,
            "year": 2024 if index % 2 else 2023,
            "has_abstract": True,
            "publication_types": [["Systematic Review"], ["Practice Guideline"], ["Randomized Controlled Trial"], ["Journal Article"]][index % 4],
        }
        for index in range(24)
    ]
    async with factory() as setup:
        setup.add(LiteratureSearchResult(query="q", total_count=len(items), items_json=json.dumps(items)))
        await setup.commit()
    async with factory() as active:
        yield active
    await engine.dispose()


@pytest.mark.asyncio
async def test_ac_rp_13_replan_preserves_read_key_locked_and_manual(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    first = await service.generate(1, PlanGenerateRequest())
    plan = await service.repo.plan(first.id)
    protected = plan.items[0]
    protected.is_locked = True
    protected.role = "core"
    await service.add_manual(1, plan.id, ManualItemCreate(pmid=plan.items[-1].pmid))
    session.add(LiteratureSearchItemState(result_id=1, pmid=protected.pmid, read_status="read", is_key=True, read_at=None, tags_json="[]"))
    await session.commit()

    replanned = await service.replan(1, plan.id, PlanGenerateRequest(preserve=True))
    new_plan = await service.repo.plan(replanned.id)
    kept = next(item for item in new_plan.items if item.pmid == protected.pmid)
    assert kept.is_locked and kept.role == "core"
    assert next(item for item in new_plan.items if item.pmid == plan.items[-1].pmid).source == "manual"

    reset = await service.replan(1, new_plan.id, PlanGenerateRequest(preserve=False))
    reset_plan = await service.repo.plan(reset.id)
    assert next(item for item in reset_plan.items if item.pmid == plan.items[-1].pmid).source == "system"


@pytest.mark.asyncio
async def test_ac_rp_16_consolidated_excludes_only_folded_duplicate(session: AsyncSession) -> None:
    group = LiteratureDuplicateGroup(trigger_task_id=1, result_id=1, match_method="pmid", confidence="clear", status="auto_merged")
    session.add(group)
    await session.flush()
    session.add_all([
        LiteratureDuplicateGroupMember(group_id=group.id, result_id=1, record_pmid="60000000", canonical_result_id=1, canonical_record_pmid="60000000", source_search_ids_json="[]"),
        LiteratureDuplicateGroupMember(group_id=group.id, result_id=1, record_pmid="60000001", canonical_result_id=1, canonical_record_pmid="60000000", source_search_ids_json="[]"),
    ])
    await session.commit()
    plan = await ReadingPlanService(session).generate(1, PlanGenerateRequest(duplicate_mode="consolidated"))
    persisted = await ReadingPlanService(session).repo.plan(plan.id)
    assert "60000000" in {item.pmid for item in persisted.items}
    assert "60000001" not in {item.pmid for item in persisted.items}


@pytest.mark.asyncio
async def test_ac_rp_17_metric_filter_and_unconfigured_status(session: AsyncSession) -> None:
    batch = JournalMetricImportBatch(edition_year=2025, provider="test", provider_version="1", source_filename="x.csv", source_file_hash="a" * 64, license_provenance="test", status="active", is_active=True)
    session.add(batch)
    await session.flush()
    session.add(LiteratureCommercialJournalMetric(import_batch_id=batch.id, journal_key="metric", issn="1234-5678", normalized_journal_name="metric journal", metric_year=2025, impact_factor=8.0, jcr_best_quartile="Q1", wos_indexes_json='["SCIE"]', cas_quartile="1区", status="matched"))
    await session.commit()
    service = ReadingPlanService(session)
    plan = await service.generate(1, PlanGenerateRequest())
    page = await service.candidates(1, plan.id, "overview", 1, 100, None, None, None, "Q1", "SCIE", "1区", 5.0)
    assert page.total >= 1
    assert all(item.journal_metrics["status"] == "matched" for item in page.items)


@pytest.mark.asyncio
async def test_ac_rp_17_candidates_search_filter_pagination_and_total(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    plan = await service.generate(1, PlanGenerateRequest())
    all_candidates = await service.candidates(
        1, plan.id, "frontier", 1, 100, None, None, None
    )
    assert all_candidates.total > 2
    target = all_candidates.items[1]
    by_title = await service.candidates(
        1, plan.id, "frontier", 1, 100, target.title, None, None
    )
    by_author = await service.candidates(
        1, plan.id, "frontier", 1, 100, target.authors[0], None, None
    )
    by_pmid = await service.candidates(
        1, plan.id, "frontier", 1, 100, target.pmid, None, None
    )
    by_year_and_type = await service.candidates(
        1, plan.id, "frontier", 1, 100, None, target.year, "Journal Article"
    )
    page = await service.candidates(1, plan.id, "frontier", 2, 1, None, None, None)
    assert by_title.total == by_author.total == by_pmid.total == 1
    assert all(item.year == target.year for item in by_year_and_type.items)
    assert page.total == all_candidates.total and len(page.items) == 1


@pytest.mark.asyncio
async def test_ac_rp_20_cross_result_and_invalid_stage_are_rejected(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    plan = await service.generate(1, PlanGenerateRequest())
    with pytest.raises(NotFoundError):
        await service.get(999, plan.id)
    with pytest.raises(UnprocessableEntityError):
        await service.save_order(1, plan.id, "not-a-stage", [])


@pytest.mark.asyncio
async def test_ac_rp_21_active_detail_uses_bounded_queries(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    await service.generate(1, PlanGenerateRequest())
    count = 0
    def observe(*_args) -> None:
        nonlocal count
        count += 1
    event.listen(session.sync_session.bind, "before_cursor_execute", observe)
    try:
        await service.active(1)
    finally:
        event.remove(session.sync_session.bind, "before_cursor_execute", observe)
    assert count <= 8


@pytest.mark.asyncio
async def test_ac_rp_21_candidate_pool_uses_bounded_queries(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    plan = await service.generate(1, PlanGenerateRequest())
    count = 0

    def observe(*_args) -> None:
        nonlocal count
        count += 1

    event.listen(session.sync_session.bind, "before_cursor_execute", observe)
    try:
        await service.candidates(1, plan.id, "frontier", 1, 20, None, None, None)
    finally:
        event.remove(session.sync_session.bind, "before_cursor_execute", observe)
    assert count <= 8


@pytest.mark.asyncio
async def test_ac_rp_15_failed_generation_leaves_previous_active(session: AsyncSession, monkeypatch) -> None:
    service = ReadingPlanService(session)
    first = await service.generate(1, PlanGenerateRequest())
    await session.commit()
    async def fail_archive(_result_id: int) -> None:
        raise RuntimeError("simulated activation failure")
    monkeypatch.setattr(service.repo, "archive_active", fail_archive)
    with pytest.raises(RuntimeError):
        await service.generate(1, PlanGenerateRequest())
    await session.rollback()
    plans = list((await session.scalars(select(ReadingPlan).where(ReadingPlan.result_id == 1))).all())
    assert [plan.id for plan in plans if plan.status == "active"] == [first.id]


@pytest.mark.asyncio
async def test_ac_rp_12_expand_and_replace_are_explicit(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    plan_read = await service.generate(1, PlanGenerateRequest())
    plan = await service.repo.plan(plan_read.id)
    candidate = next(item for item in plan.items if item.role == "candidate")
    expanded = await service.promote(
        1,
        plan.id,
        candidate.stage,
        PromoteCoreRequest(pmid=candidate.pmid, strategy="expand"),
    )
    assert expanded.total_core_count == 13
    replacement = next(item for item in plan.items if item.role == "core")
    second_candidate = next(item for item in plan.items if item.role == "candidate")
    replaced = await service.promote(
        1,
        plan.id,
        second_candidate.stage,
        PromoteCoreRequest(
            pmid=second_candidate.pmid,
            strategy="replace",
            replace_pmid=replacement.pmid,
        ),
    )
    assert replaced.total_core_count == 13


@pytest.mark.asyncio
async def test_ac_rp_11_complete_stage_order_persists(session: AsyncSession) -> None:
    service = ReadingPlanService(session)
    read = await service.generate(1, PlanGenerateRequest())
    plan = await service.repo.plan(read.id)
    stage = next(
        stage for stage in ("overview", "clinical_decision", "primary_evidence", "frontier")
        if sum(item.stage == stage and item.role == "core" for item in plan.items) > 1
    )
    pmids = [item.pmid for item in plan.items if item.stage == stage and item.role == "core"]
    saved = await service.save_order(1, plan.id, stage, list(reversed(pmids)))
    returned = next(value for value in saved.stages if value.stage == stage)
    assert [item.pmid for item in returned.core] == list(reversed(pmids))


@pytest.mark.asyncio
async def test_ac_rp_05_persisted_plan_has_one_role_per_unique_pmid(
    session: AsyncSession,
) -> None:
    service = ReadingPlanService(session)
    generated = await service.generate(1, PlanGenerateRequest())
    plan = await service.repo.plan(generated.id)
    assert len(plan.items) == len({item.pmid for item in plan.items})
    assert {item.role for item in plan.items}.issubset({"core", "candidate"})


def test_ac_rp_09_legacy_reading_status_is_safely_normalized() -> None:
    legacy = LiteratureSearchItemState(
        result_id=1,
        pmid="legacy",
        saved=False,
        read_status="reading",
        tags_json="[]",
        in_reading_plan=False,
        is_key=False,
        read_at=None,
    )
    state = LiteratureSearchService._to_state_read(legacy)
    assert state.read_status == "unread"
    assert state.read_at is None
