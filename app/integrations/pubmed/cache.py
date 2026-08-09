"""进程内 TTL 内存缓存。

设计说明：NCBI E-utilities 对同一结果重复请求既不经济也增加被限流风险；
用规范化参数作为键，命中时直接返回解析后的对象，同时避免重复解析。
"""

from __future__ import annotations

import threading
import time
from typing import Any


class TTLCache:
    """线程安全的简单 TTL 缓存（先进先删最接近过期的条目）。"""

    def __init__(
        self, default_ttl_seconds: float = 3600.0, max_entries: int = 1024
    ) -> None:
        if default_ttl_seconds <= 0:
            raise ValueError("default_ttl_seconds must be positive")
        self._default_ttl_seconds = default_ttl_seconds
        self._max_entries = max_entries
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Any | None:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            expires_at, value = item
            if time.monotonic() >= expires_at:
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl_seconds: float | None = None) -> None:
        ttl = self._default_ttl_seconds if ttl_seconds is None else ttl_seconds
        with self._lock:
            if (
                self._max_entries
                and len(self._data) >= self._max_entries
                and key not in self._data
            ):
                # 容量不足时淘汰最接近过期的一条，避免缓存无限增长。
                oldest = min(self._data, key=lambda k: self._data[k][0])
                del self._data[oldest]
            self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)
