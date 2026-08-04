"""NCBI E-utilities 速率限制器。

NCBI 官方规则：无 API Key 时最多 3 req/s（推荐 350ms 间隔），有 API Key 时 10 req/s（100ms）。
这里实现为"令牌间隔"式限流——每次调用前记录时间戳，保证相邻请求之间的间隔不小于配置值。
"""

from __future__ import annotations

import asyncio
import threading
import time


class RateLimiter:
    """基于墙钟时间的进程内请求间隔器。"""

    def __init__(self, interval_seconds: float) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be positive")
        self.interval_seconds = interval_seconds
        self._last_call_at = 0.0
        self._lock = threading.Lock()

    async def wait(self) -> None:
        """阻塞到下一个允许的请求时刻。

        设计说明：请求间隔必须按"请求进入时刻"计算而不是按完成时刻，
        否则慢响应会积累成突发请求；因此这里记录的是调用发起时间。
        """
        while True:
            with self._lock:
                now = time.monotonic()
                wait_seconds = self._last_call_at + self.interval_seconds - now
                if wait_seconds <= 0:
                    self._last_call_at = now
                    return
            await asyncio.sleep(wait_seconds)

    def reset(self) -> None:
        with self._lock:
            self._last_call_at = 0.0
