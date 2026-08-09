from app.modules.evaluation.answer_metrics import calculate


def test_answer_and_supported_citation() -> None:
    metrics = calculate(answer="100", reference_answer="100", cited_document_ids={1}, supporting_document_ids={1, 2}, no_answer_expected=False)
    assert metrics.correctness == 1 and metrics.citation_accuracy == 1 and metrics.citation_completeness == .5

def test_hallucinated_citation_is_visible() -> None:
    metrics = calculate(answer="A", reference_answer="A", cited_document_ids={9}, supporting_document_ids={1}, no_answer_expected=False)
    assert metrics.citation_accuracy == 0 and metrics.hallucinated_citation_rate == 1

def test_no_answer_is_scored_separately() -> None:
    metrics = calculate(answer="", reference_answer=None, cited_document_ids=set(), supporting_document_ids=set(), no_answer_expected=True)
    assert metrics.no_answer_accuracy == 1 and metrics.correctness == 1
