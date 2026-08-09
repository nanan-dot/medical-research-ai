"""注入式混合检索编排与 JSONL 审计日志。"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.rag.rrf import fuse_ranked_results
from app.rag.schemas import RetrievalResult


class TextRetriever(Protocol):
    """以原始查询文本执行检索的共同接口。"""

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        """返回已按自身分数排序的结果。"""
        ...


class HybridRetriever:
    """编排两路检索；分数只在各路内使用，跨路仅由 RRF 融合。"""

    def __init__(
        self,
        *,
        vector_retriever: TextRetriever,
        bm25_retriever: TextRetriever,
        log_path: Path | None = None,
    ) -> None:
        self._vector_retriever = vector_retriever
        self._bm25_retriever = bm25_retriever
        self._log_path = log_path

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """检索两路并执行 RRF；非正 Top-K 明确返回空且不触发后端。"""
        if top_k <= 0:
            return []
        vector_results = self._vector_retriever.search(query, top_k)
        bm25_results = self._bm25_retriever.search(query, top_k)
        fused_results = fuse_ranked_results([vector_results, bm25_results], top_k)
        self._append_log(query, vector_results, bm25_results, fused_results)
        return fused_results

    def _append_log(
        self,
        query: str,
        vector_results: list[RetrievalResult],
        bm25_results: list[RetrievalResult],
        fused_results: list[RetrievalResult],
    ) -> None:
        if self._log_path is None:
            return
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "query": query,
            "vector_top_k": [
                result.model_dump(mode="json") for result in vector_results
            ],
            "bm25_top_k": [result.model_dump(mode="json") for result in bm25_results],
            "hybrid_results": [
                result.model_dump(mode="json") for result in fused_results
            ],
        }
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")
