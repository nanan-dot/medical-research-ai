from app.modules.evaluation.retrieval_metrics import RetrievedEvidence, calculate


def test_metrics_with_multiple_relevant_documents() -> None:
    metrics = calculate([RetrievedEvidence(3, 4, "R"), RetrievedEvidence(1, 2, "Methods"), RetrievedEvidence(2)], {1, 2}, k=3, expected_page=2, expected_section="Methods")
    assert metrics.recall_at_k == 1 and metrics.precision_at_k == 2 / 3 and metrics.mrr == 1 / 2
    assert metrics.page_hit_rate == 1 and metrics.section_hit_rate == 1

def test_no_answer_and_empty_results_are_explicit() -> None:
    metrics = calculate([], set(), k=5)
    assert metrics.recall_at_k == 1 and metrics.precision_at_k == 0 and metrics.mrr == 0

def test_rejects_non_positive_k() -> None:
    try: calculate([], {1}, k=0)
    except ValueError: return
    raise AssertionError("expected ValueError")
