"""Optional local reranking while preserving retrieval scores and source identities."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from importlib.util import find_spec
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal

from app.rag.reranker import (
    BatchScorer,
    RerankCandidate,
    RerankerService,
    ScorerBusyError,
)
from app.rag.schemas import RetrievalResult
from app.rag.transformers_reranker import (
    LocalModelUnavailableError,
    create_bge_reranker,
    cross_encoder_asset_signature,
    fingerprint_cross_encoder_assets,
    validate_cross_encoder_assets,
)

RerankStatus = Literal["disabled", "applied", "fallback", "empty"]
RerankReasonCode = Literal[
    "disabled",
    "applied",
    "no_candidates",
    "model_unavailable",
    "model_busy",
    "timeout",
    "inference_error",
]


@dataclass
class NavigationRanking:
    results: list[RetrievalResult]
    scores: dict[str, float]
    status: RerankStatus
    reason_code: RerankReasonCode
    model_version: str | None = None
    latency_ms: int = 0


@dataclass(frozen=True)
class ScorerInitialization:
    scorer: BatchScorer | None
    reason_code: RerankReasonCode | None
    latency_ms: int


class _SerializedScorer:
    """Share local model loading safely across worker threads."""

    def __init__(self, scorer: BatchScorer) -> None:
        self._scorer = scorer
        self.model_version = self._scorer.model_version
        self._lock = Lock()

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not self._lock.acquire(blocking=False):
            raise ScorerBusyError("local CrossEncoder is busy")
        try:
            return self._scorer.score(query, texts)
        finally:
            self._lock.release()


_SCORER_INITIALIZATION_LOCK = Lock()


@lru_cache(maxsize=1)
def local_scorer(directory: Path) -> BatchScorer:
    """Load and cache one immutable local model for this process lifetime."""

    if not _SCORER_INITIALIZATION_LOCK.acquire(blocking=False):
        raise ScorerBusyError("local CrossEncoder initialization is already running")
    try:
        if find_spec("sentence_transformers") is None:
            raise LocalModelUnavailableError(
                "sentence-transformers dependency is unavailable"
            )
        validate_cross_encoder_assets(directory)
        signature_before = cross_encoder_asset_signature(directory)
        revision = fingerprint_cross_encoder_assets(directory)
        scorer = create_bge_reranker(directory, revision=revision)
        load = getattr(scorer, "load", None)
        if callable(load):
            load()
        signature_after = cross_encoder_asset_signature(directory)
        if signature_before != signature_after:
            raise LocalModelUnavailableError(
                "local CrossEncoder assets changed during initialization"
            )
        expected_version = f"BAAI/bge-reranker-base@{revision}"
        if scorer.model_version != expected_version:
            raise LocalModelUnavailableError(
                "local CrossEncoder fingerprint does not match the loaded model"
            )
        return _SerializedScorer(scorer)
    finally:
        _SCORER_INITIALIZATION_LOCK.release()


async def initialize_local_scorer(
    directory: Path,
    *,
    timeout_seconds: float,
    scorer_factory: Callable[[Path], BatchScorer] = local_scorer,
) -> ScorerInitialization:
    """Bound request waiting for initialization without stopping its worker thread."""

    started = monotonic()
    try:
        scorer = await asyncio.wait_for(
            asyncio.to_thread(scorer_factory, directory),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        return ScorerInitialization(
            None,
            "timeout",
            round((monotonic() - started) * 1000),
        )
    except ScorerBusyError:
        return ScorerInitialization(
            None,
            "model_busy",
            round((monotonic() - started) * 1000),
        )
    except (LocalModelUnavailableError, OSError, RuntimeError, ValueError):
        return ScorerInitialization(
            None,
            "model_unavailable",
            round((monotonic() - started) * 1000),
        )
    return ScorerInitialization(
        scorer,
        None,
        round((monotonic() - started) * 1000),
    )


async def rank_candidates(
    query: str, results: list[RetrievalResult], *, enabled: bool,
    scorer: BatchScorer | None,
    timeout_seconds: float = 5.0,
    scorer_failure_reason: RerankReasonCode = "model_unavailable",
) -> NavigationRanking:
    """Return ordered originals and separate model scores, or preserve input order."""
    if not results:
        return NavigationRanking([], {}, "empty", "no_candidates")
    if not enabled:
        return NavigationRanking(results, {}, "disabled", "disabled")
    if scorer is None:
        return NavigationRanking(results, {}, "fallback", scorer_failure_reason)
    service = RerankerService(
        scorer,
        candidate_limit=len(results),
        output_limit=len(results),
        timeout_seconds=timeout_seconds,
    )
    candidates = [RerankCandidate(item.chunk_id, item.text, rank)
                  for rank, item in enumerate(results, 1)]
    try:
        ranked = await asyncio.wait_for(
            asyncio.to_thread(service.rerank, query, candidates),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        return NavigationRanking(
            results,
            {},
            "fallback",
            "timeout",
            scorer.model_version,
            round(timeout_seconds * 1000),
        )
    if any(item.fallback for item in ranked):
        latency_ms = ranked[0].latency_ms if ranked else 0
        failure_reason = ranked[0].failure_reason if ranked else None
        reason_code: RerankReasonCode = (
            failure_reason
            if failure_reason in {"model_busy", "timeout", "inference_error"}
            else "inference_error"
        )
        return NavigationRanking(
            results,
            {},
            "fallback",
            reason_code,
            scorer.model_version,
            latency_ms,
        )
    originals = {item.chunk_id: item for item in results}
    return NavigationRanking(
        [originals[item.candidate.document_id] for item in ranked],
        {item.candidate.document_id: item.rerank_score for item in ranked
         if item.rerank_score is not None},
        "applied",
        "applied",
        scorer.model_version,
        ranked[0].latency_ms if ranked else 0,
    )
