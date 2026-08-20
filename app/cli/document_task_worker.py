"""Execute queued document operations from the durable task table."""

import argparse
import asyncio

from app.core.database import AsyncSessionLocal, engine
from app.modules.document.task_worker import DocumentTaskWorker


async def run_once() -> None:
    try:
        await DocumentTaskWorker(AsyncSessionLocal).run_once()
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process one queued task and exit.")
    parser.parse_args()
    asyncio.run(run_once())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
