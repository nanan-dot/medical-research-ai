"""Offline regression checks for navigation snapshots and reranking."""

import asyncio
import json
import threading
import time
from contextlib import nullcontext
from pathlib import Path

import numpy as np
import pytest
from safetensors.numpy import save_file

from app.modules.document_navigation.index_cache import NavigationIndexCache
from app.modules.document_navigation.ranking import rank_candidates
from app.modules.document_navigation.schema import NavigationBudget
from app.rag.reranker import ScorerBusyError
from app.rag.schemas import Chunk, RetrievalResult
from app.rag.transformers_reranker import LocalModelUnavailableError
from tests.modules.document_navigation.test_api import navigation_client  # noqa: F401


class CountingEmbedding:
    model_name = "offline-test-v1"
    dimension = 2

    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return [[float(len(text)), 1.0] for text in texts]


def chunk(text: str = "synthetic evidence", identity: str = "a") -> Chunk:
    return Chunk(chunk_id=identity, document_id=identity, text=text)


async def test_unchanged_snapshot_reuses_document_embeddings() -> None:
    cache = NavigationIndexCache()
    embedding = CountingEmbedding()
    first = await cache.get_or_build([chunk()], embedding, namespace="scope")
    second = await cache.get_or_build([chunk()], embedding, namespace="scope")
    assert first is second
    assert embedding.calls == 1


async def test_content_scope_and_model_changes_invalidate_snapshot() -> None:
    cache = NavigationIndexCache()
    embedding = CountingEmbedding()
    first = await cache.get_or_build([chunk()], embedding, namespace="scope")
    changed = await cache.get_or_build([chunk("changed")], embedding, namespace="scope")
    scoped = await cache.get_or_build([chunk()], embedding, namespace="other")
    embedding.model_name = "offline-test-v2"
    model = await cache.get_or_build([chunk()], embedding, namespace="scope")
    assert len({id(first), id(changed), id(scoped), id(model)}) == 4
    assert embedding.calls == 4


async def test_removed_document_is_not_returned_from_cached_scope() -> None:
    cache = NavigationIndexCache()
    embedding = CountingEmbedding()
    await cache.get_or_build([chunk(identity="a"), chunk(identity="b")], embedding, namespace="scope")
    remaining = await cache.get_or_build([chunk(identity="b")], embedding, namespace="scope")
    assert [item.chunk_id for item in remaining.store.search([1.0, 1.0], 10)] == ["b"]


async def test_lru_evicts_old_snapshot() -> None:
    cache = NavigationIndexCache(max_entries=1)
    embedding = CountingEmbedding()
    await cache.get_or_build([chunk()], embedding, namespace="one")
    await cache.get_or_build([chunk()], embedding, namespace="two")
    await cache.get_or_build([chunk()], embedding, namespace="one")
    assert embedding.calls == 3


async def test_oversized_snapshot_is_not_retained() -> None:
    cache = NavigationIndexCache(max_chunks=1)
    embedding = CountingEmbedding()
    for _ in range(2):
        await cache.get_or_build([chunk(identity="a"), chunk(identity="b")], embedding, namespace="scope")
    assert embedding.calls == 2


def candidates() -> list[RetrievalResult]:
    return [RetrievalResult(chunk_id=identity, text=identity, source_path="source.pdf",
                            heading="Methods", raw_score=score)
            for identity, score in [("a", 9.0), ("b", 8.0), ("c", 7.0)]]


def budget(*, sparse_top_k: int = 3) -> NavigationBudget:
    return NavigationBudget(
        dense_top_k=2,
        sparse_top_k=sparse_top_k,
        fusion_top_k=4,
        rerank_candidate_top_k=4,
        requested_limit=4,
        candidate_limit=4,
        final_limit=4,
        status="within_budget",
    )


class Scorer:
    model_version = "offline-ranking-test"

    def score(self, query: str, texts: list[str]) -> list[float]:
        return [0.1, 0.2, 0.9]


async def test_reranker_promotes_deeper_candidate_preserving_source_scores() -> None:
    original = candidates()
    ranking = await rank_candidates("query", original, enabled=True, scorer=Scorer())
    assert ranking.status == "applied"
    assert ranking.results[0] is original[2]
    assert ranking.results[0].source_path == "source.pdf"
    assert ranking.results[0].raw_score == 7.0
    assert ranking.scores["c"] == 0.9


@pytest.mark.parametrize("scores", [[float("nan"), 0.2, 0.3], [0.5]])
async def test_invalid_model_scores_preserve_retrieval_order(scores: list[float]) -> None:
    class InvalidScorer(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            return scores

    original = candidates()
    ranking = await rank_candidates("query", original, enabled=True, scorer=InvalidScorer())
    assert ranking.status == "fallback"
    assert ranking.reason_code == "inference_error"
    assert ranking.results == original
    assert ranking.scores == {}


async def test_missing_scorer_preserves_results() -> None:
    original = candidates()
    ranking = await rank_candidates("query", original, enabled=True, scorer=None)
    assert ranking.status == "fallback"
    assert ranking.reason_code == "model_unavailable"
    assert ranking.results == original


async def test_timeout_has_a_distinct_reason_code() -> None:
    class SlowScorer(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            time.sleep(0.2)
            return super().score(query, texts)

    started = time.perf_counter()
    ranking = await rank_candidates(
        "query",
        candidates(),
        enabled=True,
        scorer=SlowScorer(),
        timeout_seconds=0.01,
    )
    elapsed = time.perf_counter() - started

    assert ranking.status == "fallback"
    assert ranking.reason_code == "timeout"
    assert elapsed < 0.1


async def test_busy_model_does_not_queue_another_inference() -> None:
    class BusyScorer(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            raise ScorerBusyError("already running")

    ranking = await rank_candidates(
        "query", candidates(), enabled=True, scorer=BusyScorer()
    )

    assert ranking.status == "fallback"
    assert ranking.reason_code == "model_busy"


async def test_scorer_initialization_does_not_block_event_loop(tmp_path: Path) -> None:
    from app.modules.document_navigation.ranking import initialize_local_scorer

    events: list[str] = []

    def slow_factory(_directory: Path) -> Scorer:
        events.append("initialization_started")
        time.sleep(0.08)
        events.append("initialization_finished")
        return Scorer()

    async def heartbeat() -> None:
        await asyncio.sleep(0.01)
        events.append("event_loop_responsive")

    initialization, _ = await asyncio.gather(
        initialize_local_scorer(
            tmp_path,
            timeout_seconds=0.5,
            scorer_factory=slow_factory,
        ),
        heartbeat(),
    )

    assert initialization.reason_code is None
    assert events.index("event_loop_responsive") < events.index("initialization_finished")


async def test_initialization_timeout_keeps_singleflight_guard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.document_navigation import ranking

    started = threading.Event()
    release = threading.Event()

    class LoadableScorer(Scorer):
        model_version = "BAAI/bge-reranker-base@sha256:offline-ranking-test"

        def load(self) -> None:
            started.set()
            release.wait(timeout=1)

    monkeypatch.setattr(ranking, "find_spec", lambda _name: object())
    monkeypatch.setattr(ranking, "validate_cross_encoder_assets", lambda _path: None)
    monkeypatch.setattr(
        ranking,
        "create_bge_reranker",
        lambda _path, **_kwargs: LoadableScorer(),
    )
    monkeypatch.setattr(
        ranking,
        "cross_encoder_asset_signature",
        lambda _path: (("model.safetensors", 1, 1),),
        raising=False,
    )
    monkeypatch.setattr(
        ranking,
        "fingerprint_cross_encoder_assets",
        lambda _path: "sha256:offline-ranking-test",
    )
    ranking.local_scorer.cache_clear()

    first = await ranking.initialize_local_scorer(
        tmp_path,
        timeout_seconds=0.01,
        scorer_factory=ranking.local_scorer,
    )
    assert started.wait(timeout=0.2)
    second = await ranking.initialize_local_scorer(
        tmp_path,
        timeout_seconds=0.1,
        scorer_factory=ranking.local_scorer,
    )
    release.set()
    await asyncio.sleep(0.05)
    ranking.local_scorer.cache_clear()

    assert first.reason_code == "timeout"
    assert second.reason_code == "model_busy"


def test_model_asset_change_during_initialization_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.document_navigation import ranking

    signatures = iter(
        (
            (("model.safetensors", 1, 1),),
            (("model.safetensors", 2, 2),),
        )
    )

    class LoadableScorer(Scorer):
        model_version = "BAAI/bge-reranker-base@sha256:before"

        def load(self) -> None:
            return None

    monkeypatch.setattr(ranking, "find_spec", lambda _name: object())
    monkeypatch.setattr(ranking, "validate_cross_encoder_assets", lambda _path: None)
    monkeypatch.setattr(
        ranking,
        "create_bge_reranker",
        lambda _path, **_kwargs: LoadableScorer(),
    )
    monkeypatch.setattr(
        ranking,
        "cross_encoder_asset_signature",
        lambda _path: next(signatures),
        raising=False,
    )
    ranking.local_scorer.cache_clear()

    with pytest.raises(LocalModelUnavailableError, match="changed during initialization"):
        ranking.local_scorer(tmp_path)

    ranking.local_scorer.cache_clear()


def test_same_directory_replacement_requires_explicit_cache_invalidation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.document_navigation import ranking

    asset_state = {"revision": "sha256:first", "mtime": 1}

    class LoadableScorer(Scorer):
        def __init__(self, revision: str) -> None:
            self.model_version = f"BAAI/bge-reranker-base@{revision}"

        def load(self) -> None:
            return None

    monkeypatch.setattr(ranking, "find_spec", lambda _name: object())
    monkeypatch.setattr(ranking, "validate_cross_encoder_assets", lambda _path: None)
    monkeypatch.setattr(
        ranking,
        "cross_encoder_asset_signature",
        lambda _path: (("model.safetensors", 1, asset_state["mtime"]),),
    )
    monkeypatch.setattr(
        ranking,
        "fingerprint_cross_encoder_assets",
        lambda _path: asset_state["revision"],
    )
    monkeypatch.setattr(
        ranking,
        "create_bge_reranker",
        lambda _path, *, revision: LoadableScorer(revision),
    )
    ranking.local_scorer.cache_clear()

    first = ranking.local_scorer(tmp_path)
    asset_state.update(revision="sha256:second", mtime=2)
    still_cached = ranking.local_scorer(tmp_path)
    ranking.local_scorer.cache_clear()
    reloaded = ranking.local_scorer(tmp_path)

    assert still_cached is first
    assert first.model_version.endswith("sha256:first")
    assert reloaded.model_version.endswith("sha256:second")
    ranking.local_scorer.cache_clear()


@pytest.mark.parametrize("provider", ["dummy", "ollama"])
async def test_bm25_routes_obey_sparse_top_k(
    provider: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.document_navigation import service

    class RecordingBM25:
        def __init__(self) -> None:
            self.received_top_k: list[int] = []

        def search(self, _query: str, top_k: int) -> list[RetrievalResult]:
            self.received_top_k.append(top_k)
            return candidates()[:top_k]

    monkeypatch.setattr(service.settings, "EMBEDDING_PROVIDER", provider)
    if provider == "ollama":
        monkeypatch.setattr(
            service,
            "create_embedding_client",
            lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("offline")),
        )
    store = RecordingBM25()

    retrieval = await service.DocumentNavigationService(None)._retrieve(
        "query",
        [chunk(identity=str(index)) for index in range(10)],
        store,
        budget(sparse_top_k=3),
    )

    assert store.received_top_k == [3]
    assert [item.chunk_id for item in retrieval.sparse_candidates] == ["a", "b", "c"]


async def test_hybrid_retrieval_exposes_each_stage_in_original_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.modules.document_navigation import service

    dense = [
        RetrievalResult(
            chunk_id=identity,
            text=identity,
            source_path="dense.pdf",
            heading="",
            retriever_name="vector",
            rank=rank,
            raw_score=score,
        )
        for rank, (identity, score) in enumerate((("d1", 0.9), ("shared", 0.8)), 1)
    ]
    sparse = [
        RetrievalResult(
            chunk_id=identity,
            text=identity,
            source_path="sparse.pdf",
            heading="",
            retriever_name="bm25",
            rank=rank,
            raw_score=score,
        )
        for rank, (identity, score) in enumerate((("s1", 9.0), ("shared", 8.0)), 1)
    ]

    class FakeEmbedding:
        model_name = "fake"
        dimension = 2

        async def embed(self, _texts: list[str]) -> list[list[float]]:
            return [[1.0, 0.0]]

    class FakeStore:
        def search(self, _vector: list[float], top_k: int) -> list[RetrievalResult]:
            return dense[:top_k]

    class FakeCache:
        async def get_or_build(self, *_args: object, **_kwargs: object):
            return type(
                "Snapshot",
                (),
                {"store": FakeStore(), "lock": nullcontext(), "index_version": "index-v1"},
            )()

    class FakeBM25:
        def search(self, _query: str, top_k: int) -> list[RetrievalResult]:
            return sparse[:top_k]

    monkeypatch.setattr(service.settings, "EMBEDDING_PROVIDER", "ollama")
    monkeypatch.setattr(service, "create_embedding_client", lambda **_kwargs: FakeEmbedding())
    monkeypatch.setattr(service, "navigation_index_cache", FakeCache())

    retrieval = await service.DocumentNavigationService(None)._retrieve(
        "query",
        [chunk(identity="scope")],
        FakeBM25(),
        budget(sparse_top_k=2),
    )

    assert [item.chunk_id for item in retrieval.dense_candidates] == ["d1", "shared"]
    assert [item.chunk_id for item in retrieval.sparse_candidates] == ["s1", "shared"]
    assert [item.chunk_id for item in retrieval.results] == ["shared", "d1", "s1"]


def test_local_scorer_rejects_assets_without_a_classification_head(
    tmp_path: Path,
) -> None:
    from app.modules.document_navigation.ranking import local_scorer

    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    (tmp_path / "tokenizer.json").write_text("{}", encoding="utf-8")
    save_file({"encoder.weight": np.zeros((1, 1), dtype=np.float32)}, tmp_path / "model.safetensors")
    local_scorer.cache_clear()

    with pytest.raises(LocalModelUnavailableError, match="classification head"):
        local_scorer(tmp_path)


async def test_disabled_reranking_does_not_invoke_model() -> None:
    class UnexpectedScorer(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            raise AssertionError("disabled model must not execute")

    ranking = await rank_candidates("query", candidates(), enabled=False, scorer=UnexpectedScorer())
    assert ranking.status == "disabled"


async def test_empty_search_does_not_invoke_model() -> None:
    ranking = await rank_candidates("query", [], enabled=True, scorer=None)
    assert ranking.status == "empty"
    assert ranking.results == []


def test_api_reranks_then_deduplicates_with_source_location(
    navigation_client,  # noqa: F811
    monkeypatch,
    tmp_path: Path,
) -> None:
    from app.modules.document_navigation import service

    class ApiScorer(Scorer):
        def score(self, query: str, texts: list[str]) -> list[float]:
            return [float(len(texts) - index) for index in range(len(texts))]

    monkeypatch.setattr(service.settings, "EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setattr(service.settings, "NAVIGATION_RERANK_ENABLED", True)
    monkeypatch.setattr(service.settings, "NAVIGATION_RERANK_MODEL_DIR", service.settings.DATA_DIR)
    monkeypatch.setattr(service.settings, "RAG_TRACE_ENABLED", True)
    monkeypatch.setattr(service.settings, "RAG_TRACE_DIR", tmp_path / "trace-data")
    monkeypatch.setattr(service, "local_scorer", lambda _: ApiScorer())
    client, source_id, _ = navigation_client
    payload = client.post("/api/v1/document-navigation/search", json={
        "query": "PD-1", "limit": 1, "knowledge_source_id": source_id,
    }).json()
    assert payload["rerank_status"] == "applied"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["rerank_score"] == 2.0
    assert payload["results"][0]["location"]["page_number"] == 7
    assert payload["results"][0]["relative_path"] == "trials/liver.pdf"
    trace_file = next((tmp_path / "trace-data" / "rag_traces").glob("*.jsonl"))
    trace = json.loads(trace_file.read_text(encoding="utf-8").splitlines()[0])
    assert trace["model_version"] == "offline-ranking-test"
    assert trace["retriever_versions"]["reranker"] == "offline-ranking-test"
    assert trace["rerank_status"] == "applied"
    assert trace["rerank_reason_code"] == "applied"
    assert [item["chunk_id"] for item in trace["sparse_candidates"]] == [
        "document:1:0",
        "document:1:1",
    ]
    assert [item["chunk_id"] for item in trace["reranked_candidates"]] == [
        "document:1:0",
        "document:1:1",
    ]


def test_api_missing_model_preserves_results_and_reports_fallback(navigation_client, monkeypatch) -> None:  # noqa: F811
    from app.modules.document_navigation import service

    monkeypatch.setattr(service.settings, "EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setattr(service.settings, "NAVIGATION_RERANK_ENABLED", True)
    monkeypatch.setattr(service.settings, "NAVIGATION_RERANK_MODEL_DIR", None)
    client, _, _ = navigation_client
    payload = client.post("/api/v1/document-navigation/search", json={"query": "PD-1"}).json()
    assert payload["rerank_status"] == "fallback"
    assert payload["rerank_reason_code"] == "model_unavailable"
    assert len(payload["results"]) == 1
    assert payload["results"][0]["rerank_score"] is None
    assert "重排不可用" in payload["fallback_reason"]


def test_global_rerank_flag_does_not_enable_navigation(navigation_client, monkeypatch) -> None:  # noqa: F811
    from app.modules.document_navigation import service

    monkeypatch.setattr(service.settings, "EMBEDDING_PROVIDER", "dummy")
    monkeypatch.setattr(service.settings, "RERANK_ENABLED", True)
    monkeypatch.setattr(service.settings, "NAVIGATION_RERANK_ENABLED", False)
    monkeypatch.setattr(
        service,
        "local_scorer",
        lambda _: (_ for _ in ()).throw(AssertionError("navigation scorer must stay disabled")),
    )
    client, _, _ = navigation_client

    payload = client.post(
        "/api/v1/document-navigation/search", json={"query": "PD-1"}
    ).json()

    assert payload["rerank_status"] == "disabled"
    assert payload["rerank_reason_code"] == "disabled"
