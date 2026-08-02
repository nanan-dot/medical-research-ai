from pathlib import Path
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.core import models  # noqa: F401
from app.core.database import Base


@pytest.fixture
async def session(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'qa.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()
