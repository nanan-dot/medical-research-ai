from app.rag.orchestrator import RetrievalOrchestrator, RetrieverRoute
from app.rag.schemas import RetrievalResult


class Failing:
    def search(self, query, top_k): raise RuntimeError("down")
def test_failure_isolated_and_disabled_skipped():
    result = RetrievalOrchestrator([RetrieverRoute("bad", Failing()), RetrieverRoute("off", Failing(), False)]).search("q")
    assert result.results == [] and result.attempted_routes == ["bad"] and result.failed_routes == ["bad"]

class Static:
    def __init__(self, items): self.items = items
    def search(self, query, top_k): return self.items

def item(chunk_id, retriever):
    return RetrievalResult(chunk_id=chunk_id, text="e", source_path="test", heading="h", rank=1, raw_score=1.0, retriever_name=retriever)

def test_deduplicates_evidence_and_preserves_route_trace():
    result = RetrievalOrchestrator([RetrieverRoute("vector", Static([item("same", "vector")])), RetrieverRoute("bm25", Static([item("same", "bm25"), item("other", "bm25")]))]).search("q")
    assert [entry.chunk_id for entry in result.results] == ["same", "other"]
    assert result.attempted_routes == ["vector", "bm25"]

def test_vector_and_bm25_use_explainable_rrf():
    result = RetrievalOrchestrator([RetrieverRoute("vector", Static([item("same", "vector")])), RetrieverRoute("bm25", Static([item("same", "bm25")]))]).search("q")
    assert result.results[0].retriever_name == "hybrid"
    assert len(result.results[0].contributions) == 2
