"""论文库并发、查询次数与 Alembic 迁移验收。"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError
from app.core import models  # noqa: F401
from app.core.database import Base
from app.modules.library_item.model import LibraryItem
from app.modules.paper_library.model import PaperLibraryMember, PaperResearchRelation
from app.modules.paper_library.query import (
    PaperLibraryFilters,
    PaperLibraryView,
    PaperSort,
)
from app.modules.paper_library.schema import (
    PaperAddRequest,
    ResearchRelationUpdate,
    ResearchRole,
)
from app.modules.paper_library.service import PaperLibraryService
from app.modules.research_context.model import ResearchContext


def item(doi: str) -> LibraryItem:
    return LibraryItem(
        pmid=None,
        doi=doi,
        source_search_id=None,
        fulltext_status="metadata_only",
        fulltext_status_reason="test",
    )


@pytest.mark.asyncio
async def test_list_query_count_is_constant_as_page_grows(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'queries.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        papers = [item(f"10.1000/query-{index}") for index in range(10)]
        session.add_all(papers)
        await session.flush()
        session.add_all(
            PaperLibraryMember(
                library_item_id=paper.id,
                import_source="external_identifier",
            )
            for paper in papers
        )
        await session.commit()

    counts: list[int] = []
    for limit in (1, 10):
        query_count = 0

        def count_query(*_args: object) -> None:
            nonlocal query_count
            query_count += 1

        event.listen(engine.sync_engine, "before_cursor_execute", count_query)
        async with factory() as session:
            await PaperLibraryService(session).list_items(
                view=PaperLibraryView.ALL,
                filters=PaperLibraryFilters(),
                offset=0,
                limit=limit,
                sort=PaperSort.ADDED_AT,
            )
        event.remove(engine.sync_engine, "before_cursor_execute", count_query)
        counts.append(query_count)

    assert counts[0] == counts[1]
    assert counts[1] <= 6
    await engine.dispose()


@pytest.mark.asyncio
async def test_independent_sessions_allow_only_one_relation_version_update(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'relation-race.db').as_posix()}",
        connect_args={"timeout": 10},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        paper = item("10.1000/relation-race")
        research = ResearchContext(name="Race", description=None)
        session.add_all([paper, research])
        await session.flush()
        session.add(
            PaperResearchRelation(
                library_item_id=paper.id,
                research_context_id=research.id,
                role="to_evaluate",
                version=1,
            )
        )
        session.add(
            PaperLibraryMember(
                library_item_id=paper.id,
                import_source="external_identifier",
            )
        )
        await session.commit()
        paper_id, research_id = paper.id, research.id

    async def update(role: ResearchRole) -> str:
        async with factory() as session:
            try:
                await PaperLibraryService(session).upsert_relation(
                    paper_id,
                    research_id,
                    ResearchRelationUpdate(
                        role=role, note=None, expected_version=1
                    ),
                )
                await session.commit()
                return "success"
            except ConflictError:
                await session.rollback()
                return "conflict"

    outcomes = await asyncio.gather(
        update(ResearchRole.CORE_EVIDENCE),
        update(ResearchRole.BACKGROUND_SUPPORT),
    )
    assert sorted(outcomes) == ["conflict", "success"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_identifier_add_is_idempotent(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'add-race.db').as_posix()}",
        connect_args={"timeout": 10},
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    async def add() -> tuple[str, int]:
        async with factory() as session:
            result = await PaperLibraryService(session).add(
                PaperAddRequest(doi="10.1000/concurrent")
            )
            await session.commit()
            return result.outcome, result.item.id

    results = await asyncio.gather(add(), add())
    assert {result[0] for result in results} == {"created", "already_exists"}
    assert len({result[1] for result in results}) == 1
    await engine.dispose()


def test_v31_migration_upgrades_real_alembic_schema(tmp_path: Path) -> None:
    database_url = f"sqlite+aiosqlite:///{(tmp_path / 'v31-migration.db').as_posix()}"
    environment = {**os.environ, "DATABASE_URL": database_url, "PYTHONPATH": ""}
    project_root = Path(__file__).resolve().parents[3]
    for command in (
        ("upgrade", "f1b3c5d7e9a2"),
        ("upgrade", "a2c4e6f8b0d1"),
        ("downgrade", "f1b3c5d7e9a2"),
        ("upgrade", "a2c4e6f8b0d1"),
    ):
        completed = subprocess.run(
            [sys.executable, "-m", "alembic", *command],
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
