"""Rule-based retrieval metrics against human-annotated evidence."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedEvidence:
    document_id: int
    page: int | None = None
    section: str | None = None

@dataclass(frozen=True)
class RetrievalMetrics:
    recall_at_k: float
    precision_at_k: float
    mrr: float
    page_hit_rate: float | None
    section_hit_rate: float | None
    evidence_count: int

def calculate(retrieved: list[RetrievedEvidence], relevant_document_ids: set[int], *, k: int, expected_page: int | None = None, expected_section: str | None = None) -> RetrievalMetrics:
    """Calculate document relevance and optional locator hits; no-answer items have no relevance set."""
    if k < 1: raise ValueError("k must be positive")
    top_k = retrieved[:k]
    hits = [item for item in top_k if item.document_id in relevant_document_ids]
    recall = len({item.document_id for item in hits}) / len(relevant_document_ids) if relevant_document_ids else 1.0
    precision = len(hits) / len(top_k) if top_k else 0.0
    first_rank = next((index + 1 for index, item in enumerate(top_k) if item.document_id in relevant_document_ids), None)
    page_rate = None if expected_page is None else float(any(item.page == expected_page and item.document_id in relevant_document_ids for item in top_k))
    section_rate = None if expected_section is None else float(any(item.section == expected_section and item.document_id in relevant_document_ids for item in top_k))
    return RetrievalMetrics(recall, precision, 0.0 if first_rank is None else 1 / first_rank, page_rate, section_rate, len(top_k))
