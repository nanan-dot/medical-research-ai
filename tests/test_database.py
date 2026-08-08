"""SQLAlchemy 模型注册与异步会话事务测试。"""

from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import database, models  # noqa: F401 - register all models
from app.core.database import Base


EXPECTED_TABLES = {
    "conversations",
    "messages",
    "citations",
    "documents",
    "evaluations",
    "exports",
    "feedbacks",
    "healths",
    "knowledge_sources",
    "literature_searchs",
    "literature_search_results",
    "literature_search_tasks",
    "literature_search_task_results",
    "literature_search_item_state",
    "literature_duplicate_groups",
    "literature_duplicate_group_members",
    "literature_duplicate_resolutions",
    "literature_reading_orders",
    "library_items",
    "comparison_tasks",
    "comparison_cells",
    "evidence_matrices",
    "matrix_documents",
    "matrix_fields",
    "matrix_cells",
    "model_configs",
    "paper_analysiss",
    "research_directions",
    "feasibility_scores",
    "feasibility_weight_profiles",
    "advisor_reviews",
    "direction_revisions",
    "presentations",
    "outlines",
    "research_conditions",
    "research_conditions_versions",
    "topic_structurings",
    "topic_structuring_versions",
    "writings",
}


def test_all_models_are_registered():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


@pytest.mark.asyncio
async def test_sqlite_file_is_created(tmp_path: Path):
    database_path = tmp_path / "app.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    await engine.dispose()
    assert database_path.is_file()


@pytest.mark.asyncio
async def test_get_session_rolls_back_on_exception(tmp_path: Path, monkeypatch):
    database_path = tmp_path / "rollback.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    session_factory = async_sessionmaker(test_engine, expire_on_commit=False)

    async with test_engine.begin() as connection:
        await connection.execute(text("CREATE TABLE rollback_probe (value INTEGER)"))

    monkeypatch.setattr(database, "AsyncSessionLocal", session_factory)
    session_dependency = database.get_session()
    session = await anext(session_dependency)
    await session.execute(text("INSERT INTO rollback_probe (value) VALUES (1)"))

    with pytest.raises(RuntimeError, match="force rollback"):
        await session_dependency.athrow(RuntimeError("force rollback"))

    async with session_factory() as verification_session:
        result = await verification_session.execute(text("SELECT COUNT(*) FROM rollback_probe"))
        assert result.scalar_one() == 0

    await test_engine.dispose()
