"""注入式混合检索编排与 JSONL 审计日志。"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.core.config import settings
from app.rag.rrf import fuse_ranked_results
from app.rag.schemas import RetrievalResult
from app.rag.trace import TracePolicy


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
        trace_policy: TracePolicy | None = None,
    ) -> None:
        self._vector_retriever = vector_retriever
        self._bm25_retriever = bm25_retriever
        self._log_path = log_path
        self._trace_policy = trace_policy or TracePolicy(data_dir=settings.DATA_DIR)
        if log_path is not None:
            try:
                log_path.resolve().relative_to(self._trace_policy.data_dir.resolve())
            except ValueError as error:
                raise ValueError("retrieval log path must stay under trace DATA_DIR") from error

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        dense_top_k: int | None = None,
        sparse_top_k: int | None = None,
        fusion_top_k: int | None = None,
    ) -> list[RetrievalResult]:
        """检索两路并执行 RRF；非正 Top-K 明确返回空且不触发后端。"""
        if top_k <= 0:
            return []
        vector_results = self._vector_retriever.search(query, dense_top_k or top_k)
        bm25_results = self._bm25_retriever.search(query, sparse_top_k or top_k)
        fused_results = fuse_ranked_results(
            [vector_results, bm25_results], fusion_top_k or top_k
        )
        self._append_log(query, vector_results, bm25_results, fused_results)
        return fused_results[:top_k]

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
            "query": query if self._trace_policy.store_query else None,
            "vector_top_k": [
                _safe_log_result(result, self._trace_policy) for result in vector_results
            ],
            "bm25_top_k": [
                _safe_log_result(result, self._trace_policy) for result in bm25_results
            ],
            "hybrid_results": [
                _safe_log_result(result, self._trace_policy) for result in fused_results
            ],
        }
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        with self._log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _safe_log_result(result: RetrievalResult, policy: TracePolicy) -> dict[str, object]:
    """旧 JSONL 调试日志仅保留可追溯标识，不默认保存正文或本机路径。"""

    data = result.model_dump(mode="json", exclude={"text"})
    data["source_path"] = Path(result.source_path.replace("\\", "/")).name
    if policy.store_text:
        data["text"] = result.text[: policy.max_text_chars]
    return data
