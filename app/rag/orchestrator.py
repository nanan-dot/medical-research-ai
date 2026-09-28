"""Failure-isolated orchestration for existing text retrievers."""
from dataclasses import dataclass, field
from time import perf_counter

from app.rag.hybrid_retriever import TextRetriever
from app.rag.reranker import RerankCandidate, RerankerService
from app.rag.rrf import fuse_ranked_results
from app.rag.schemas import RetrievalResult


@dataclass(frozen=True)
class RetrieverRoute:
    name: str
    retriever: TextRetriever
    enabled: bool = True
    # 是否参与 RRF 融合。None=按名称推断（vector/bm25 默认参与），
    # 显式 True/False 覆盖推断——避免硬编码名字字符串导致新路由静默不融合。
    use_rrf: bool | None = None


@dataclass(frozen=True)
class OrchestrationResult:
    results: list[RetrievalResult]
    attempted_routes: list[str]
    failed_routes: list[str]
    route_reasons: dict[str, str] = field(default_factory=dict)
    stage_elapsed_ms: dict[str, int] = field(default_factory=dict)


class RetrievalOrchestrator:
    """Combines independent routes without allowing one failure to erase evidence."""

    def __init__(
        self, routes: list[RetrieverRoute], reranker: RerankerService | None = None
    ) -> None:
        self._routes = routes
        self._reranker = reranker

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        candidate_top_k: int | None = None,
        fusion_top_k: int | None = None,
    ) -> OrchestrationResult:
        if top_k <= 0:
            return OrchestrationResult([], [], [])
        candidate_limit = candidate_top_k or top_k
        fusion_limit = fusion_top_k or top_k
        seen: set[str] = set()
        results: list[RetrievalResult] = []
        attempted: list[str] = []
        failed: list[str] = []
        reasons: dict[str, str] = {}
        elapsed: dict[str, int] = {}
        rrf_sets: list[list[RetrievalResult]] = []
        for route in self._routes:
            if not route.enabled:
                continue
            attempted.append(route.name)
            started = perf_counter()
            try:
                route_results = route.retriever.search(query, candidate_limit)
                # use_rrf 为 None 时按名称推断（兼容既有 vector/bm25 路由），
                # 显式 True/False 覆盖推断。
                use_rrf = (
                    route.use_rrf
                    if route.use_rrf is not None
                    else route.name in {"vector", "bm25"}
                )
                if use_rrf:
                    rrf_sets.append(route_results)
                for item in route_results:
                    if item.chunk_id not in seen:
                        seen.add(item.chunk_id)
                        results.append(item)
            except (RuntimeError, TimeoutError, ValueError):
                failed.append(route.name)
                reasons[route.name] = "route_unavailable"
            finally:
                elapsed[route.name] = round((perf_counter() - started) * 1000)
        try:
            # RRF 融合 + 其余成功路由结果合并去重：任何一路的成功证据都不被抹掉。
            fused = fuse_ranked_results(rrf_sets, fusion_limit) if rrf_sets else results[:fusion_limit]
            fused_ids = {item.chunk_id for item in fused}
            for item in results:
                if item.chunk_id not in fused_ids:
                    fused.append(item)
            fused = fused[:fusion_limit]
            if self._reranker is not None and fused:
                ranked = self._reranker.rerank(
                    query,
                    [RerankCandidate(item.chunk_id, item.text, item.rank) for item in fused],
                )
                by_id = {item.chunk_id: item for item in fused}
                fused = [
                    by_id[item.candidate.document_id].model_copy(
                        update={"rank": item.new_rank}
                    )
                    for item in ranked
                ]
        except (RuntimeError, TimeoutError, ValueError):
            # 融合或重排失败时回退到原始检索结果，不因后处理崩溃而抹掉全部证据。
            fused = results[:top_k]
        return OrchestrationResult(fused[:top_k], attempted, failed, reasons, elapsed)
