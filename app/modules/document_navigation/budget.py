"""Hard candidate budgets for document navigation retrieval stages."""

from app.modules.document_navigation.schema import NavigationBudget


def resolve_navigation_budget(
    *,
    requested_limit: int,
    available_chunks: int,
    dense_top_k: int,
    sparse_top_k: int,
    fusion_top_k: int,
    rerank_candidate_top_k: int,
) -> NavigationBudget:
    """Resolve explicit stage caps without silently increasing configured values."""

    if min(
        requested_limit,
        dense_top_k,
        sparse_top_k,
        fusion_top_k,
        rerank_candidate_top_k,
    ) <= 0 or available_chunks < 0:
        raise ValueError("navigation budgets must be positive and chunks non-negative")
    configured_candidate_cap = min(fusion_top_k, rerank_candidate_top_k)
    candidate_limit = min(available_chunks, configured_candidate_cap)
    final_limit = min(requested_limit, candidate_limit)
    return NavigationBudget(
        dense_top_k=dense_top_k,
        sparse_top_k=sparse_top_k,
        fusion_top_k=fusion_top_k,
        rerank_candidate_top_k=rerank_candidate_top_k,
        requested_limit=requested_limit,
        candidate_limit=candidate_limit,
        final_limit=final_limit,
        status=(
            "limited"
            if requested_limit > configured_candidate_cap
            else "within_budget"
        ),
    )
