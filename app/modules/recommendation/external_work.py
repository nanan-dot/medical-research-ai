"""Bounded concurrency primitives for optional recommendation enrichments."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable


async def bounded_async_map[InputT, OutputT](
    values: Iterable[InputT],
    function: Callable[[InputT], Awaitable[OutputT]],
    *,
    limit: int,
) -> list[OutputT]:
    if limit < 1:
        raise ValueError("concurrency limit must be positive")
    semaphore = asyncio.Semaphore(limit)

    async def invoke(value: InputT) -> OutputT:
        async with semaphore:
            return await function(value)

    return await asyncio.gather(*(invoke(value) for value in values))
