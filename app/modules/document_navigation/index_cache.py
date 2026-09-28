"""Bounded process-local snapshots keyed by source content and embedding identity."""

import asyncio
import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from app.rag.embeddings import EmbeddingClient
from app.rag.faiss_store import FaissIndexStore
from app.rag.schemas import Chunk


@dataclass
class IndexSnapshot:
    """Published indexes are immutable; serialize reads for the store contract."""

    store: FaissIndexStore
    index_version: str
    lock: Lock = field(default_factory=Lock)


class NavigationIndexCache:
    """LRU snapshots with a total chunk budget; no medical text is persisted."""

    def __init__(self, max_entries: int = 4, max_chunks: int = 4096) -> None:
        if max_entries < 1 or max_chunks < 1:
            raise ValueError("cache budgets must be positive")
        self._max_entries = max_entries
        self._max_chunks = max_chunks
        self._entries: OrderedDict[str, IndexSnapshot] = OrderedDict()
        self._lock = Lock()

    async def get_or_build(
        self, chunks: list[Chunk], embedding: EmbeddingClient, *, namespace: str
    ) -> IndexSnapshot:
        """Reuse an exact snapshot; failures are never cached or published."""
        # 文档范围、正文和模型身份都参与指纹，删除或修改资料不会命中旧索引。
        payload = [namespace, embedding.model_name, embedding.dimension,
                   [chunk.model_dump(exclude={"vector_id"}) for chunk in chunks]]
        key = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        with self._lock:
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]
        vectors = await embedding.embed([chunk.text for chunk in chunks])
        store = FaissIndexStore(
            Path("unused-navigation-memory-index"),
            dimension=embedding.dimension, embedding_model=embedding.model_name,
        )
        await asyncio.to_thread(store.build, chunks, vectors)
        snapshot = IndexSnapshot(store, key)
        if len(chunks) > self._max_chunks:
            return snapshot
        with self._lock:
            # 同时首次请求允许各自构建，发布时复用已有快照，避免跨事件循环锁。
            if key in self._entries:
                self._entries.move_to_end(key)
                return self._entries[key]
            self._entries[key] = snapshot
            while (len(self._entries) > self._max_entries or
                   sum(item.store.size for item in self._entries.values()) > self._max_chunks):
                self._entries.popitem(last=False)
        return snapshot


navigation_index_cache = NavigationIndexCache()
