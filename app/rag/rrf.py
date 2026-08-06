"""Reciprocal Rank Fusion 的纯函数实现。"""

from collections.abc import Iterable
from typing import Literal

from app.rag.schemas import RetrievalContribution, RetrievalResult

RRF_K = 60


def fuse_ranked_results(
    ranked_result_sets: Iterable[list[RetrievalResult]], top_k: int
) -> list[RetrievalResult]:
    """以各路排名进行 RRF 融合，并按 chunk_id 合并可追溯贡献。"""
    if top_k <= 0:
        return []
    merged: dict[str, tuple[RetrievalResult, float, list[RetrievalContribution]]] = {}
    for result_set in ranked_result_sets:
        for result in result_set:
            if result.raw_score is None:
                continue
            contribution = RetrievalContribution(
                retriever_name=_as_base_retriever_name(result.retriever_name),
                rank=result.rank,
                raw_score=result.raw_score,
            )
            contribution_score = 1 / (RRF_K + result.rank)
            existing = merged.get(result.chunk_id)
            if existing is None:
                merged[result.chunk_id] = (result, contribution_score, [contribution])
                continue
            representative, accumulated_score, contributions = existing
            merged[result.chunk_id] = (
                representative,
                accumulated_score + contribution_score,
                contributions + [contribution],
            )
    sorted_results = sorted(merged.values(), key=lambda item: -item[1])
    return [
        representative.model_copy(
            update={
                "retriever_name": "hybrid",
                "rank": index + 1,
                "fused_score": fused_score,
                "contributions": contributions,
            }
        )
        for index, (representative, fused_score, contributions) in enumerate(sorted_results[:top_k])
    ]


def _as_base_retriever_name(retriever_name: str) -> Literal["vector", "bm25"]:
    """显式收窄路由名，避免将扩展的字符串值写入可追溯贡献。"""
    if retriever_name == "vector":
        return "vector"
    if retriever_name == "bm25":
        return "bm25"
    raise ValueError("RRF accepts only vector or bm25 ranked results")
