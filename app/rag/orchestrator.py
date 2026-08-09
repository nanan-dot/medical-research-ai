"""Failure-isolated orchestration for existing text retrievers."""
from dataclasses import dataclass

from app.rag.hybrid_retriever import TextRetriever
from app.rag.reranker import RerankCandidate, RerankerService
from app.rag.rrf import fuse_ranked_results
from app.rag.schemas import RetrievalResult


@dataclass(frozen=True)
class RetrieverRoute:
    name: str
    retriever: TextRetriever
    enabled: bool = True

@dataclass(frozen=True)
class OrchestrationResult:
    results: list[RetrievalResult]
    attempted_routes: list[str]
    failed_routes: list[str]

class RetrievalOrchestrator:
    """Combines independent routes without allowing one failure to erase evidence."""
    def __init__(self, routes: list[RetrieverRoute], reranker: RerankerService | None = None) -> None: self._routes = routes; self._reranker = reranker
    def search(self, query: str, top_k: int = 5) -> OrchestrationResult:
        if top_k <= 0: return OrchestrationResult([], [], [])
        seen: set[str] = set(); results: list[RetrievalResult] = []; attempted: list[str] = []; failed: list[str] = []; rrf_sets: list[list[RetrievalResult]] = []
        for route in self._routes:
            if not route.enabled: continue
            attempted.append(route.name)
            try:
                route_results = route.retriever.search(query, top_k)
                if route.name in {"vector", "bm25"}: rrf_sets.append(route_results)
                for item in route_results:
                    if item.chunk_id not in seen:
                        seen.add(item.chunk_id); results.append(item)
            except (RuntimeError, TimeoutError, ValueError): failed.append(route.name)
        fused = fuse_ranked_results(rrf_sets, top_k) if rrf_sets else results[:top_k]
        if self._reranker is not None and fused:
            ranked = self._reranker.rerank(query, [RerankCandidate(item.chunk_id, item.text, item.rank) for item in fused])
            by_id = {item.chunk_id: item for item in fused}
            fused = [by_id[item.candidate.document_id].model_copy(update={"rank": item.new_rank}) for item in ranked]
        return OrchestrationResult(fused, attempted, failed)
