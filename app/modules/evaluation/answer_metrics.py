"""Auditable rule-based answer and citation evaluation metrics."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AnswerMetrics:
    correctness: float
    answer_relevance: float
    citation_accuracy: float
    citation_completeness: float
    no_answer_accuracy: float
    hallucinated_citation_rate: float

def calculate(*, answer: str, reference_answer: str | None, cited_document_ids: set[int], supporting_document_ids: set[int], no_answer_expected: bool) -> AnswerMetrics:
    """Score normalized exact-reference overlap and citation sets; human review remains required."""
    normalized_answer, normalized_reference = answer.strip().casefold(), (reference_answer or "").strip().casefold()
    abstained = not normalized_answer
    no_answer_accuracy = float(abstained == no_answer_expected)
    if no_answer_expected:
        return AnswerMetrics(no_answer_accuracy, no_answer_accuracy, 1.0 if not cited_document_ids else 0.0, 1.0, no_answer_accuracy, float(bool(cited_document_ids)))
    correctness = float(bool(normalized_reference) and normalized_answer == normalized_reference)
    relevance = float(bool(normalized_reference) and (normalized_reference in normalized_answer or normalized_answer in normalized_reference))
    supported = cited_document_ids & supporting_document_ids
    accuracy = len(supported) / len(cited_document_ids) if cited_document_ids else 0.0
    completeness = len(supported) / len(supporting_document_ids) if supporting_document_ids else 1.0
    hallucinated = len(cited_document_ids - supporting_document_ids) / len(cited_document_ids) if cited_document_ids else 0.0
    return AnswerMetrics(correctness, relevance, accuracy, completeness, no_answer_accuracy, hallucinated)
