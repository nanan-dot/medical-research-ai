"""Build and persist minimized retrieval traces for document navigation."""

import asyncio
from typing import Literal

from app.modules.document_navigation.schema import (
    NavigationBudget,
    NavigationCondition,
    NavigationStrategy,
)
from app.rag.schemas import (
    Constraint,
    EvidenceSet,
    QueryPlan,
    RankedEvidence,
    RetrievalTrace,
)
from app.rag.trace import trace_store_from_settings


async def record_navigation_trace(
    *,
    query: str,
    knowledge_source_id: int | None,
    conditions: list[NavigationCondition],
    strategy: NavigationStrategy,
    budget: NavigationBudget,
    dense_candidates: list[RankedEvidence],
    sparse_candidates: list[RankedEvidence],
    fused_candidates: list[RankedEvidence],
    reranked: list[RankedEvidence],
    selected: list[RankedEvidence],
    rerank_status: Literal["disabled", "applied", "fallback", "empty"],
    rerank_reason_code: Literal[
        "disabled",
        "applied",
        "no_candidates",
        "model_unavailable",
        "model_busy",
        "timeout",
        "inference_error",
    ],
    fallback_reason: str | None,
    latency_by_stage: dict[str, int],
    index_version: str,
    model_version: str | None,
) -> str | None:
    """Persist one trace under the central privacy policy when tracing is enabled."""

    store = trace_store_from_settings()
    if store is None:
        return None
    selected_ids = {item.chunk_id for item in selected}
    rejected = [
        item
        for item in (reranked or fused_candidates)
        if item.chunk_id not in selected_ids
    ]
    trace = RetrievalTrace(
        query_original=query,
        query_plan=QueryPlan(
            query=query,
            constraints=[
                Constraint(
                    field=condition.field or condition.condition_id,
                    value=condition.expected_value or condition.label,
                    status="required",
                )
                for condition in conditions
            ],
            profile="document_navigation",
        ),
        profile="document_navigation",
        rerank_status=rerank_status,
        rerank_reason_code=rerank_reason_code,
        filters={
            "knowledge_source_id": knowledge_source_id,
            "effective_indexed_only": True,
            "candidate_budget": budget.model_dump(mode="json"),
        },
        retriever_versions={
            "strategy": strategy.value,
            **({"reranker": model_version} if model_version else {}),
        },
        dense_candidates=dense_candidates,
        sparse_candidates=sparse_candidates,
        rrf_candidates=(
            fused_candidates if strategy == NavigationStrategy.HYBRID else []
        ),
        reranked_candidates=reranked,
        selected_evidence=EvidenceSet(
            evidence=selected,
            status="ready" if selected else "insufficient_evidence",
        ),
        rejected_evidence=rejected,
        fallbacks=[fallback_reason] if fallback_reason else [],
        latency_by_stage=latency_by_stage,
        index_version=index_version,
        model_version=model_version,
    )
    stored = await asyncio.to_thread(store.append, trace)
    return stored.trace_id
