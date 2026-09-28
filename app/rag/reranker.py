"""Configurable reranking with safe fallback to retrieval order."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from time import monotonic
from typing import Literal, Protocol

from app.rag.exceptions import NotesRAGError


class ScorerBusyError(RuntimeError):
    """The process-local scorer is still serving an earlier inference."""


RerankFailureReason = Literal[
    "model_unavailable", "model_busy", "timeout", "inference_error"
]


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
    failure_reason: RerankFailureReason | None = None

class BatchScorer(Protocol):
    model_version: str
    def score(self, query: str, texts: list[str]) -> list[float]: ...

class RerankerService:
    """Owns policy; scorer is injected so local/cloud implementations remain explicit."""
    def __init__(self, scorer: BatchScorer | None, *, enabled: bool = True, candidate_limit: int = 50, output_limit: int = 10, timeout_seconds: float = 5.0) -> None:
        self.scorer, self.enabled, self.candidate_limit, self.output_limit, self.timeout_seconds = scorer, enabled, candidate_limit, output_limit, timeout_seconds
        self._cache: dict[tuple[str, tuple[tuple[str, str], ...], str, str], list[float]] = {}

    def rerank(self, query: str, candidates: list[RerankCandidate]) -> list[RerankResult]:
        selected = candidates[: self.candidate_limit]
        if not selected:
            return []
        started = monotonic()
        if not self.enabled or self.scorer is None:
            return self._fallback(selected, 0, "model_unavailable")
        key = (
            query,
            tuple((item.document_id, item.text) for item in selected),
            self.scorer.model_version,
            getattr(self.scorer, "config_version", "scorer-v1"),
        )
        try:
            scores = self._cache.get(key)
            if scores is None:
                scores = self.scorer.score(query, [item.text for item in selected])
                if len(scores) != len(selected):
                    raise ValueError("scorer returned an invalid score count")
                if any(not isfinite(float(score)) for score in scores):
                    raise ValueError("scorer returned a non-finite score")
                self._cache[key] = scores
            elapsed = round((monotonic() - started) * 1000)
            # 注意：scorer 是同步阻塞调用，此处的 elapsed 是调用返回后的测量值；
            # 无法中断真正挂死的 scorer。该阈值语义为"可接受的最大延迟"——
            # 超时后回退到检索序，但不保证提前终止阻塞调用。
            if elapsed > self.timeout_seconds * 1000:
                return self._fallback(selected, elapsed, "timeout")
            ordered = sorted(zip(selected, scores, strict=True), key=lambda item: (-item[1], item[0].original_rank))[: self.output_limit]
            return [RerankResult(item, score, index + 1, self.scorer.model_version, elapsed, False) for index, (item, score) in enumerate(ordered)]
        except ScorerBusyError:
            return self._fallback(
                selected, round((monotonic() - started) * 1000), "model_busy"
            )
        except (NotesRAGError, RuntimeError, TimeoutError, TypeError, ValueError):
            # 已收敛的模型异常、超时和无效分数均保持检索顺序，避免破坏上游。
            return self._fallback(
                selected,
                round((monotonic() - started) * 1000),
                "inference_error",
            )

    def _fallback(
        self,
        candidates: list[RerankCandidate],
        latency_ms: int,
        reason: RerankFailureReason,
    ) -> list[RerankResult]:
        return [
            RerankResult(
                item,
                None,
                index + 1,
                "unavailable",
                latency_ms,
                True,
                reason,
            )
            for index, item in enumerate(candidates[: self.output_limit])
        ]
