from datetime import UTC, datetime, timedelta

from app.rag.schemas import (
    EvidenceSet,
    GroundedAnswer,
    GroundedCitation,
    QueryPlan,
    RankedEvidence,
    RetrievalTrace,
)
from app.rag.trace import TracePolicy, TraceStore, replay_candidate_ids


def _evidence(chunk_id: str, rank: int, *, source_path: str = "C:/private/paper.pdf") -> RankedEvidence:
    return RankedEvidence(
        document_id="domain-document",
        chunk_id=chunk_id,
        source_path=source_path,
        text_original="private literature text " * 20,
        rank=rank,
        index_version="index-v1",
    )


def _trace(**updates: object) -> RetrievalTrace:
    values: dict[str, object] = {
        "trace_id": "trace-1",
        "query_original": "PD-L1 TPS >= 50%",
        "query_plan": QueryPlan(query="PD-L1 TPS >= 50%", profile="local_evidence"),
        "profile": "local_evidence",
        "rerank_status": "fallback",
        "rerank_reason_code": "model_busy",
        "dense_candidates": [_evidence("dense", 2)],
        "sparse_candidates": [_evidence("sparse", 1)],
        "rrf_candidates": [_evidence("rrf", 1)],
        "selected_evidence": EvidenceSet(evidence=[_evidence("selected", 1)]),
        "fallbacks": ["bm25_route_unavailable"],
        "latency_by_stage": {"dense": 11, "sparse": 7},
        "answer": GroundedAnswer(answer="grounded answer", trace_id="trace-1"),
        "citations": [
            GroundedCitation(
                citation_id="selected",
                document_id="domain-document",
                chunk_id="selected",
                source_path="C:/private/paper.pdf",
            )
        ],
        "index_version": "index-v1",
    }
    values.update(updates)
    return RetrievalTrace(**values)


def test_wp8_trace_persists_answer_candidates_and_fallbacks(tmp_path) -> None:
    store = TraceStore(TracePolicy(data_dir=tmp_path, store_query=True, store_text=True))
    stored = store.append(_trace())

    loaded = store.get(stored.trace_id)

    assert loaded is not None
    assert loaded.answer is not None and loaded.answer.answer == "grounded answer"
    assert loaded.dense_candidates[0].chunk_id == "dense"
    assert loaded.selected_evidence.evidence[0].chunk_id == "selected"
    assert loaded.fallbacks == ["bm25_route_unavailable"]
    assert loaded.rerank_status == "fallback"
    assert loaded.rerank_reason_code == "model_busy"


def test_wp8_trace_links_returned_answer_to_replayable_evidence(tmp_path) -> None:
    store = TraceStore(TracePolicy(data_dir=tmp_path, store_query=True, store_text=True))
    trace, answer = store.append_answer(_trace(), GroundedAnswer(answer="final"))

    loaded = store.get(answer.trace_id or "")

    assert answer.trace_id == trace.trace_id
    assert loaded is not None and loaded.answer is not None
    assert loaded.selected_evidence.evidence[0].chunk_id == "selected"


def test_wp8_trace_privacy_defaults_redact_secrets_text_query_and_absolute_paths(tmp_path) -> None:
    store = TraceStore(TracePolicy(data_dir=tmp_path))
    trace = _trace(filters={"Authorization": "Bearer secret", "cookie": "private"})

    stored = store.append(trace)
    serialized = next((tmp_path / "rag_traces").glob("*.jsonl")).read_text("utf-8")

    assert stored.query_original is None
    assert stored.query_plan is not None and stored.query_plan.query == "[not_persisted]"
    assert stored.dense_candidates[0].text_original == ""
    assert stored.dense_candidates[0].source_path == "paper.pdf"
    assert "secret" not in serialized and "private" not in serialized
    assert "C:/private" not in serialized


def test_wp8_trace_applies_candidate_and_text_limits(tmp_path) -> None:
    store = TraceStore(
        TracePolicy(data_dir=tmp_path, store_query=True, store_text=True, max_candidates=1, max_text_chars=12)
    )
    trace = _trace(dense_candidates=[_evidence("first", 1), _evidence("second", 2)])

    stored = store.append(trace)

    assert [candidate.chunk_id for candidate in stored.dense_candidates] == ["first"]
    assert len(stored.dense_candidates[0].text_original) == 12


def test_wp8_replay_order_is_deterministic_for_fixed_trace() -> None:
    trace = _trace(rrf_candidates=[_evidence("z", 1), _evidence("a", 1), _evidence("b", 2)])

    assert replay_candidate_ids(trace) == ["a", "z", "b"]


def test_wp8_trace_schema_is_backward_compatible() -> None:
    trace = RetrievalTrace(query_plan=QueryPlan(query="legacy"))

    assert trace.schema_version == "rag-trace-v1"
    assert trace.dense_candidates == [] and trace.fallbacks == []


def test_wp8_trace_retention_cleanup_stays_under_data_dir(tmp_path) -> None:
    store = TraceStore(TracePolicy(data_dir=tmp_path, retention_days=1))
    old_trace = _trace(recorded_at=datetime.now(UTC) - timedelta(days=2))
    store.append(old_trace)

    removed = store.purge_expired(now=datetime.now(UTC))

    assert removed == 1
    assert list((tmp_path / "rag_traces").glob("*.jsonl")) == []
