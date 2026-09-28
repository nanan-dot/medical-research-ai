from app.rag.reranker import RerankCandidate, RerankerService, ScorerBusyError


class Scorer:
    model_version = "local-test"
    def score(self, query: str, texts: list[str]) -> list[float]: return [float(len(text)) for text in texts]

def candidates() -> list[RerankCandidate]: return [RerankCandidate("a", "a", 1), RerankCandidate("b", "long", 2)]
def test_reranks_and_retains_original_rank_metadata() -> None:
    results = RerankerService(Scorer()).rerank("q", candidates())
    assert results[0].candidate.document_id == "b" and results[0].candidate.original_rank == 2
def test_empty_and_disabled_fallback() -> None:
    assert RerankerService(Scorer()).rerank("q", []) == []
    assert RerankerService(None).rerank("q", candidates())[0].fallback
def test_invalid_scorer_degrades_to_original_order() -> None:
    class Bad(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]: return []
    assert RerankerService(Bad()).rerank("q", candidates())[0].candidate.document_id == "a"


def test_non_finite_scorer_result_degrades_to_original_order() -> None:
    class Bad(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            return [float("nan")] * len(texts)

    assert RerankerService(Bad()).rerank("q", candidates())[0].candidate.document_id == "a"


def test_busy_scorer_reports_structured_fallback() -> None:
    class Busy(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            raise ScorerBusyError("busy")

    result = RerankerService(Busy()).rerank("q", candidates())[0]

    assert result.fallback is True
    assert result.failure_reason == "model_busy"
