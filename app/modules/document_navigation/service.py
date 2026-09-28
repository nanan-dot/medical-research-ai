"""Aggregate indexed local documents into an explainable RAG navigation request."""

import asyncio
from dataclasses import dataclass
from time import monotonic

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document.parsers.schemas import ParsedDocument
from app.modules.document_navigation.budget import resolve_navigation_budget
from app.modules.document_navigation.conditions import (
    requested_navigation_conditions,
)
from app.modules.document_navigation.corpus import (
    SourceDocument,
    format_navigation_results,
    make_navigation_chunks,
    scope_index_version,
    to_ranked_evidence_list,
)
from app.modules.document_navigation.index_cache import navigation_index_cache
from app.modules.document_navigation.ranking import (
    initialize_local_scorer,
    local_scorer,
    rank_candidates,
)
from app.modules.document_navigation.schema import (
    DocumentNavigationRequest,
    DocumentNavigationResponse,
    NavigationBudget,
    NavigationCondition,
    NavigationStrategy,
)
from app.modules.document_navigation.trace import record_navigation_trace
from app.modules.document_upload.model import DocumentAsset
from app.modules.knowledge_source.model import KnowledgeSource
from app.rag.bm25_store import BM25Store
from app.rag.embeddings import create_embedding_client
from app.rag.exceptions import NotesRAGError
from app.rag.hybrid_retriever import HybridRetriever, TextRetriever
from app.rag.schemas import Chunk, RetrievalResult
from app.rag.vector_retriever import VectorRetriever


@dataclass(frozen=True)
class NavigationRetrieval:
    """Preserve every retrieval stage for budgets, reranking, and audit traces."""

    results: list[RetrievalResult]
    strategy: NavigationStrategy
    fallback_reason: str | None
    index_version: str
    dense_candidates: list[RetrievalResult]
    sparse_candidates: list[RetrievalResult]


class _CapturingRetriever:
    """Capture a retriever's exact ordered output without changing its behavior."""

    def __init__(self, retriever: TextRetriever) -> None:
        self._retriever = retriever
        self.results: list[RetrievalResult] = []

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        self.results = self._retriever.search(query, top_k)
        return self.results


class DocumentNavigationService:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(self, request: DocumentNavigationRequest) -> DocumentNavigationResponse:
        started = monotonic()
        query = request.query.strip()
        documents = await self._load_documents(request)
        chunks, contexts = make_navigation_chunks(documents)
        conditions = requested_navigation_conditions(query)
        budget = _budget_for(request.limit, len(chunks))
        latency = {"load_and_chunk": _elapsed_ms(started)}
        if not chunks:
            empty_reason = "当前范围没有可用于跨文档检索的已解析且已索引资料。"
            latency["total"] = _elapsed_ms(started)
            trace_id = await record_navigation_trace(
                query=query,
                knowledge_source_id=request.knowledge_source_id,
                conditions=conditions,
                strategy=NavigationStrategy.BM25,
                budget=budget,
                dense_candidates=[],
                sparse_candidates=[],
                fused_candidates=[],
                reranked=[],
                selected=[],
                rerank_status="empty",
                rerank_reason_code="no_candidates",
                fallback_reason=empty_reason,
                latency_by_stage=latency,
                index_version=scope_index_version(chunks),
                model_version=None,
            )
            return _empty_response(
                request,
                query,
                len(documents),
                conditions,
                budget,
                empty_reason,
                trace_id,
            )

        index_started = monotonic()
        bm25 = BM25Store()
        bm25.build(chunks)
        latency["lexical_index"] = _elapsed_ms(index_started)

        retrieval_started = monotonic()
        retrieval = await self._retrieve(
            query, chunks, bm25, budget
        )
        results = retrieval.results
        strategy = retrieval.strategy
        fallback_reason = retrieval.fallback_reason
        index_version = retrieval.index_version
        budget = _effective_budget_for_strategy(
            budget,
            strategy,
            available_chunks=len(chunks),
        )
        latency["retrieve"] = _elapsed_ms(retrieval_started)

        model_dir = settings.NAVIGATION_RERANK_MODEL_DIR
        scorer = None
        initialization_reason = None
        initialization_started = monotonic()
        if results and settings.NAVIGATION_RERANK_ENABLED and model_dir:
            initialization = await initialize_local_scorer(
                model_dir,
                timeout_seconds=(
                    settings.NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS
                ),
                scorer_factory=local_scorer,
            )
            scorer = initialization.scorer
            initialization_reason = initialization.reason_code
        latency["rerank_initialize"] = _elapsed_ms(initialization_started)

        rerank_started = monotonic()
        ranked = await rank_candidates(
            query,
            results,
            enabled=settings.NAVIGATION_RERANK_ENABLED,
            scorer=scorer,
            timeout_seconds=settings.NAVIGATION_RERANK_TIMEOUT_SECONDS,
            scorer_failure_reason=initialization_reason or "model_unavailable",
        )
        latency["rerank_inference"] = _elapsed_ms(rerank_started)
        if ranked.status == "fallback":
            if ranked.reason_code == "timeout" and initialization_reason == "timeout":
                rerank_reason = (
                    "本地重排初始化超过 "
                    f"{settings.NAVIGATION_RERANK_INITIALIZATION_TIMEOUT_SECONDS:g} "
                    "秒等待阈值，保留原检索顺序。"
                )
            elif ranked.reason_code == "timeout":
                rerank_reason = (
                    f"本地重排超过 {settings.NAVIGATION_RERANK_TIMEOUT_SECONDS:g} "
                    "秒推理等待阈值，保留原检索顺序。"
                )
            elif ranked.reason_code == "model_busy":
                rerank_reason = "本地重排模型正忙，已保留原检索顺序。"
            else:
                rerank_reason = "本地重排不可用，保留原检索顺序。"
            fallback_reason = _join_reason(
                fallback_reason, rerank_reason
            )
        if budget.status == "limited":
            fallback_reason = _join_reason(
                fallback_reason, "请求结果数超过当前候选预算，已按显式上限返回。"
            )

        navigation_results, selected_chunk_ids = format_navigation_results(
            ranked.results, contexts, conditions, ranked.scores, budget.final_limit
        )
        dense_evidence = to_ranked_evidence_list(
            retrieval.dense_candidates, contexts, index_version
        )
        sparse_evidence = to_ranked_evidence_list(
            retrieval.sparse_candidates, contexts, index_version
        )
        fused_evidence = to_ranked_evidence_list(results, contexts, index_version)
        reranked_evidence = (
            to_ranked_evidence_list(ranked.results, contexts, index_version)
            if ranked.status == "applied"
            else []
        )
        selected_evidence = [
            item
            for item in (reranked_evidence or fused_evidence)
            if item.chunk_id in selected_chunk_ids
        ]
        latency["total"] = _elapsed_ms(started)
        trace_id = await record_navigation_trace(
            query=query,
            knowledge_source_id=request.knowledge_source_id,
            conditions=conditions,
            strategy=strategy,
            budget=budget,
            dense_candidates=dense_evidence,
            sparse_candidates=sparse_evidence,
            fused_candidates=fused_evidence,
            reranked=reranked_evidence,
            selected=selected_evidence,
            rerank_status=ranked.status,
            rerank_reason_code=ranked.reason_code,
            fallback_reason=fallback_reason,
            latency_by_stage=latency,
            index_version=index_version,
            model_version=ranked.model_version,
        )
        return DocumentNavigationResponse(
            query=query,
            knowledge_source_id=request.knowledge_source_id,
            indexed_only=request.indexed_only,
            effective_indexed_only=True,
            searchable_document_count=len(documents),
            strategy=strategy,
            fallback_reason=fallback_reason,
            rerank_status=ranked.status,
            rerank_reason_code=ranked.reason_code,
            candidate_budget=budget,
            trace_id=trace_id,
            conditions=conditions,
            results=navigation_results,
        )

    async def _load_documents(
        self, request: DocumentNavigationRequest
    ) -> list[SourceDocument]:
        statement = (
            select(Document, KnowledgeSource, DocumentAsset)
            .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
            .outerjoin(DocumentAsset, DocumentAsset.document_id == Document.id)
            .where(
                Document.parse_status == "succeeded",
                Document.parsed_content.is_not(None),
                KnowledgeSource.enabled.is_(True),
                Document.index_status == "succeeded",
                Document.paperqa_index_key.is_not(None),
                Document.paperqa_index_key != "",
            )
            .order_by(Document.id)
        )
        # 当前跨文档导航只允许已索引资料；响应显式返回 effective_indexed_only。
        if request.knowledge_source_id is not None:
            statement = statement.where(
                Document.knowledge_source_id == request.knowledge_source_id
            )
        rows = (await self._session.execute(statement)).all()
        documents: list[SourceDocument] = []
        for document, source, asset in rows:
            try:
                parsed = ParsedDocument.model_validate_json(document.parsed_content)
            except ValueError:
                continue
            documents.append(SourceDocument(document, source, asset, parsed))
        return documents

    async def _retrieve(
        self,
        query: str,
        chunks: list[Chunk],
        bm25: BM25Store,
        budget: NavigationBudget,
    ) -> NavigationRetrieval:
        scope_version = scope_index_version(chunks)
        if settings.EMBEDDING_PROVIDER != "ollama":
            sparse_candidates = _matched_bm25(
                bm25, query, _sparse_candidate_limit(budget, len(chunks))
            )
            return NavigationRetrieval(
                results=sparse_candidates,
                strategy=NavigationStrategy.BM25,
                fallback_reason="本机语义向量未启用，已使用可解释的 BM25 词法检索。",
                index_version=scope_version,
                dense_candidates=[],
                sparse_candidates=sparse_candidates,
            )
        try:
            embedding = create_embedding_client(
                provider="ollama",
                base_url=settings.OLLAMA_BASE_URL,
                model=settings.OLLAMA_EMBEDDING_MODEL,
                dimension=settings.EMBEDDING_DIMENSION,
            )
            snapshot = await navigation_index_cache.get_or_build(
                chunks,
                embedding,
                namespace=f"{settings.DATA_DIR.resolve()}|{settings.OLLAMA_BASE_URL}",
            )
            query_vector = (await embedding.embed([query]))[0]
            vector = VectorRetriever(
                index_store=snapshot.store, embed_query=lambda _: query_vector
            )
            captured_vector = _CapturingRetriever(vector)
            captured_bm25 = _CapturingRetriever(bm25)

            def search_snapshot() -> list[RetrievalResult]:
                with snapshot.lock:
                    return HybridRetriever(
                        vector_retriever=captured_vector,
                        bm25_retriever=captured_bm25,
                    ).search(
                        query,
                        budget.candidate_limit,
                        dense_top_k=budget.dense_top_k,
                        sparse_top_k=budget.sparse_top_k,
                        fusion_top_k=budget.fusion_top_k,
                    )

            results = await asyncio.to_thread(search_snapshot)
            return NavigationRetrieval(
                results=results,
                strategy=NavigationStrategy.HYBRID,
                fallback_reason=None,
                index_version=snapshot.index_version,
                dense_candidates=captured_vector.results,
                sparse_candidates=captured_bm25.results,
            )
        except (NotesRAGError, RuntimeError, ValueError, OSError):
            sparse_candidates = _matched_bm25(
                bm25, query, _sparse_candidate_limit(budget, len(chunks))
            )
            return NavigationRetrieval(
                results=sparse_candidates,
                strategy=NavigationStrategy.BM25,
                fallback_reason="本机语义向量不可用，已降级为 BM25。",
                index_version=scope_version,
                dense_candidates=[],
                sparse_candidates=sparse_candidates,
            )


def _budget_for(requested_limit: int, available_chunks: int) -> NavigationBudget:
    return resolve_navigation_budget(
        requested_limit=requested_limit,
        available_chunks=available_chunks,
        dense_top_k=settings.NAVIGATION_DENSE_TOP_K,
        sparse_top_k=settings.NAVIGATION_SPARSE_TOP_K,
        fusion_top_k=settings.NAVIGATION_FUSION_TOP_K,
        rerank_candidate_top_k=settings.NAVIGATION_RERANK_CANDIDATE_TOP_K,
    )


def _matched_bm25(
    store: BM25Store, query: str, limit: int
) -> list[RetrievalResult]:
    """Exclude BM25's deterministic zero-score padding from navigation results."""

    return [
        result
        for result in store.search(query, limit)
        if (result.raw_score or 0) > 0
    ]


def _sparse_candidate_limit(
    budget: NavigationBudget,
    available_chunks: int,
) -> int:
    """Apply the sparse stage cap before later fusion/rerank candidate caps."""

    return min(
        available_chunks,
        budget.sparse_top_k,
        budget.rerank_candidate_top_k,
    )


def _effective_budget_for_strategy(
    budget: NavigationBudget,
    strategy: NavigationStrategy,
    *,
    available_chunks: int,
) -> NavigationBudget:
    """Report the effective route cap instead of a larger downstream-only cap."""

    if strategy != NavigationStrategy.BM25:
        return budget
    configured_candidate_cap = min(
        budget.sparse_top_k,
        budget.rerank_candidate_top_k,
    )
    candidate_limit = min(available_chunks, configured_candidate_cap)
    return budget.model_copy(
        update={
            "candidate_limit": candidate_limit,
            "final_limit": min(budget.requested_limit, candidate_limit),
            "status": (
                "limited"
                if budget.requested_limit > configured_candidate_cap
                else "within_budget"
            ),
        }
    )


def _empty_response(
    request: DocumentNavigationRequest,
    query: str,
    count: int,
    conditions: list[NavigationCondition],
    budget: NavigationBudget,
    fallback_reason: str,
    trace_id: str | None,
) -> DocumentNavigationResponse:
    return DocumentNavigationResponse(
        query=query,
        knowledge_source_id=request.knowledge_source_id,
        indexed_only=request.indexed_only,
        effective_indexed_only=True,
        searchable_document_count=count,
        strategy=NavigationStrategy.BM25,
        fallback_reason=fallback_reason,
        rerank_status="empty",
        rerank_reason_code="no_candidates",
        candidate_budget=budget,
        trace_id=trace_id,
        conditions=conditions,
        results=[],
    )


def _join_reason(current: str | None, addition: str) -> str:
    return "；".join(filter(None, [current, addition]))


def _elapsed_ms(started: float) -> int:
    return max(0, round((monotonic() - started) * 1000))
