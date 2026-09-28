"""Isolated SQLite persistence fixture for A0 acceptance tests."""

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app
from tests.modules.document_anchor.support import create_document


@pytest.fixture(autouse=True)
def configured_extractor(monkeypatch, tmp_path):
    import json

    command = json.dumps(
        [
            "node",
            str(
                Path(__file__).resolve().parents[3]
                / "tools/pdf_textitem_extractor/dist/cli.js"
            ),
        ]
    )
    monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_COMMAND", command)
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")


@pytest.fixture
def api_context(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'api.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare():
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with factory() as session:
            document, path = await create_document(session, tmp_path / "source")
            await session.commit()
            return document.id, path

    async def override():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except BaseException:
                await session.rollback()
                raise

    document_id, path = asyncio.run(prepare())
    app.dependency_overrides[get_session] = override
    try:
        with TestClient(app) as client:
            yield client, document_id, path
    finally:
        app.dependency_overrides.pop(get_session, None)
        asyncio.run(engine.dispose())


@pytest.fixture
async def session(tmp_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'anchor.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as test_session:
        yield test_session
    await engine.dispose()
