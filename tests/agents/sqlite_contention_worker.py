"""Subprocess worker for the M0 SQLite BEGIN IMMEDIATE contention gate."""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

REPO_ROOT = Path(__file__).parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agents.transaction import ImmediateUnitOfWork


async def increment(database: Path, iterations: int) -> None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database.as_posix()}",
        connect_args={"timeout": 30},
    )
    try:
        for _ in range(iterations):
            async with ImmediateUnitOfWork(engine) as uow:
                assert uow.session is not None
                await uow.session.execute(
                    text("UPDATE m0_contention_probe SET value = value + 1 WHERE id = 1")
                )
                await uow.commit()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(increment(Path(sys.argv[1]), int(sys.argv[2])))
