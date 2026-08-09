"""Configurable reranking with safe fallback to retrieval order."""
from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Protocol


@dataclass(frozen=True)
class RerankCandidate:
    document_id: str
    text: str
    original_rank: int

@dataclass(frozen=True)
class RerankResult:
    candidate: RerankCandidate
    rerank_score: float | None
    new_rank: int
    model_version: str
    latency_ms: int
    fallback: bool

class BatchScorer(Protocol):
    model_version: str
    def score(self, query: str, texts: list[str]) -> list[float]: ...

class RerankerService:
    """Owns policy; scorer is injected so local/cloud implementations remain explicit."""
    def __init__(self, scorer: BatchScorer | None, *, enabled: bool = True, candidate_limit: int = 50, output_limit: int = 10, timeout_seconds: float = 5.0) -> None:
        self.scorer, self.enabled, self.candidate_limit, self.output_limit, self.timeout_seconds = scorer, enabled, candidate_limit, output_limit, timeout_seconds
        self._cache: dict[tuple[str, tuple[str, ...]], list[float]] = {}

    def rerank(self, query: str, candidates: list[RerankCandidate]) -> list[RerankResult]:
        selected = candidates[: self.candidate_limit]
        if not selected: return []
        started = monotonic()
        if not self.enabled or self.scorer is None: return self._fallback(selected, 0)
        key = (query, tuple(item.document_id for item in selected))
        try:
            scores = self._cache.get(key)
            if scores is None:
                scores = self.scorer.score(query, [item.text for item in selected])
                if len(scores) != len(selected): raise ValueError("scorer returned an invalid score count")
                self._cache[key] = scores
            elapsed = round((monotonic() - started) * 1000)
            if elapsed > self.timeout_seconds * 1000: return self._fallback(selected, elapsed)
            ordered = sorted(zip(selected, scores, strict=True), key=lambda item: (-item[1], item[0].original_rank))[: self.output_limit]
            return [RerankResult(item, score, index + 1, self.scorer.model_version, elapsed, False) for index, (item, score) in enumerate(ordered)]
        except (RuntimeError, TimeoutError, ValueError):
            return self._fallback(selected, round((monotonic() - started) * 1000))

    def _fallback(self, candidates: list[RerankCandidate], latency_ms: int) -> list[RerankResult]:
        return [RerankResult(item, None, index + 1, "unavailable", latency_ms, True) for index, item in enumerate(candidates[: self.output_limit])]
