"""混合检索编排的行为测试。"""

import json
from pathlib import Path
from typing import Literal

import pytest

from app.rag.hybrid_retriever import HybridRetriever
from app.rag.schemas import RetrievalResult


class StaticRetriever:
    """只在检索器边界替代向量系统，保持融合算法使用真实实现。"""

    def __init__(self, results: list[RetrievalResult]) -> None:
        self._results = results

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        return self._results[:top_k]


def _result(
    chunk_id: str,
    retriever_name: Literal["vector", "bm25"],
    rank: int,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        text=chunk_id,
        source_path="/notes/example.md",
        heading="Example",
        retriever_name=retriever_name,
        rank=rank,
        raw_score=1.0,
        fused_score=None,
    )


def test_search_fuses_both_retrievers_and_deduplicates_same_chunk() -> None:
    retriever = HybridRetriever(
        vector_retriever=StaticRetriever([_result("same", "vector", 1)]),
        bm25_retriever=StaticRetriever([_result("same", "bm25", 1)]),
    )

    results = retriever.search("EGFR", top_k=1)

    assert len(results) == 1
    assert results[0].retriever_name == "hybrid"
    assert results[0].chunk_id == "same"


def test_search_handles_empty_retriever_result() -> None:
    retriever = HybridRetriever(
        vector_retriever=StaticRetriever([]),
        bm25_retriever=StaticRetriever([_result("bm25-only", "bm25", 1)]),
    )

    results = retriever.search("EGFR", top_k=1)

    assert results[0].chunk_id == "bm25-only"


def test_search_writes_traceable_jsonl_log(tmp_path: Path) -> None:
    log_path = tmp_path / "retrieval.jsonl"
    retriever = HybridRetriever(
        vector_retriever=StaticRetriever([_result("vector", "vector", 1)]),
        bm25_retriever=StaticRetriever([_result("bm25", "bm25", 1)]),
        log_path=log_path,
    )

    retriever.search("EGFR", top_k=1)

    payload = json.loads(log_path.read_text(encoding="utf-8"))
    assert payload["query"] == "EGFR"
    assert payload["vector_top_k"][0]["rank"] == 1
    assert payload["hybrid_results"][0]["retriever_name"] == "hybrid"


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_returns_empty_for_non_positive_top_k(top_k: int) -> None:
    retriever = HybridRetriever(
        vector_retriever=StaticRetriever([_result("vector", "vector", 1)]),
        bm25_retriever=StaticRetriever([_result("bm25", "bm25", 1)]),
    )

    assert retriever.search("EGFR", top_k=top_k) == []
