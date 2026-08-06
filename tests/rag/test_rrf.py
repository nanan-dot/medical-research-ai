"""RRF 融合的行为测试。"""

import pytest
from typing import Literal

from app.rag.rrf import RRF_K, fuse_ranked_results
from app.rag.schemas import RetrievalResult


def _result(
    chunk_id: str,
    retriever_name: Literal["vector", "bm25"],
    rank: int,
    raw_score: float,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        text=f"text for {chunk_id}",
        source_path="/notes/example.md",
        heading="Example",
        retriever_name=retriever_name,
        rank=rank,
        raw_score=raw_score,
        fused_score=None,
    )


def test_fuse_ranked_results_uses_rrf_ranks_not_raw_scores() -> None:
    vector = [_result("shared", "vector", 1, 9999.0)]
    bm25 = [_result("shared", "bm25", 2, 0.01)]

    results = fuse_ranked_results([vector, bm25], top_k=1)

    assert results[0].fused_score == pytest.approx(1 / (RRF_K + 1) + 1 / (RRF_K + 2))


def test_fuse_ranked_results_deduplicates_same_chunk_and_keeps_contributions() -> None:
    vector = [_result("shared", "vector", 1, 2.0)]
    bm25 = [_result("shared", "bm25", 1, 4.0)]

    results = fuse_ranked_results([vector, bm25], top_k=10)

    assert len(results) == 1
    assert results[0].chunk_id == "shared"
    assert results[0].retriever_name == "hybrid"


@pytest.mark.parametrize("top_k", [0, -1])
def test_fuse_ranked_results_returns_empty_for_non_positive_top_k(top_k: int) -> None:
    results = fuse_ranked_results([[_result("one", "vector", 1, 1.0)]], top_k=top_k)

    assert results == []
