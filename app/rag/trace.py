"""受限的 RAG 检索轨迹持久化；只写项目 ``DATA_DIR`` 下的 JSONL。"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.rag.schemas import (
    EvidenceSet,
    GroundedAnswer,
    GroundedCitation,
    RankedEvidence,
    RetrievalCandidate,
    RetrievalTrace,
)

TRACE_DIRECTORY_NAME = "rag_traces"
NOT_PERSISTED = "[not_persisted]"
REDACTED = "[REDACTED]"
SENSITIVE_KEYS = frozenset(
    {"api_key", "apikey", "authorization", "cookie", "password", "secret", "token"}
)


@dataclass(frozen=True)
class TracePolicy:
    """控制本地轨迹的最小化采集、大小与保留时间。"""

    data_dir: Path
    store_query: bool = False
    store_text: bool = False
    max_candidates: int = 50
    max_text_chars: int = 500
    retention_days: int = 30

    def __post_init__(self) -> None:
        if self.max_candidates <= 0 or self.max_text_chars < 0 or self.retention_days < 0:
            raise ValueError("trace policy limits must be non-negative and candidates positive")


class TraceStore:
    """JSONL 轨迹仓库；读取、清理和写入均限制在应用数据目录。"""

    def __init__(self, policy: TracePolicy) -> None:
        self._policy = policy

    def append(self, trace: RetrievalTrace) -> RetrievalTrace:
        """脱敏、限长后写入一条轨迹，并返回实际持久化的记录。"""

        stored = sanitize_trace(trace, self._policy)
        path = self._path_for(stored.recorded_at)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as trace_file:
            trace_file.write(stored.model_dump_json() + "\n")
        return stored

    def append_answer(
        self, trace: RetrievalTrace, answer: GroundedAnswer
    ) -> tuple[RetrievalTrace, GroundedAnswer]:
        """把答案与其候选证据写入同一 Trace，并返回携带 trace_id 的答案。"""

        linked_answer = answer.model_copy(update={"trace_id": trace.trace_id})
        stored = self.append(
            trace.model_copy(
                update={
                    "answer": linked_answer,
                    "citations": linked_answer.citations,
                }
            )
        )
        return stored, linked_answer.model_copy(update={"trace_id": stored.trace_id})

    def get(self, trace_id: str) -> RetrievalTrace | None:
        """按 ID 查询本地轨迹，调用方可由 fallback/latency 定位降级原因。"""

        for path in sorted(self._trace_directory().glob("*.jsonl"), reverse=True):
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = RetrievalTrace.model_validate_json(line)
                if record.trace_id == trace_id:
                    return record
        return None

    def purge_expired(self, *, now: datetime | None = None) -> int:
        """按保留策略删除到期 JSONL 条目；不使用任何系统级计划任务。"""

        cutoff = (now or datetime.now(UTC)) - timedelta(days=self._policy.retention_days)
        removed = 0
        for path in self._trace_directory().glob("*.jsonl"):
            retained: list[str] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = RetrievalTrace.model_validate_json(line)
                if record.recorded_at < cutoff:
                    removed += 1
                else:
                    retained.append(record.model_dump_json())
            if retained:
                path.write_text("\n".join(retained) + "\n", encoding="utf-8")
            elif path.exists():
                path.unlink()
        return removed

    def _path_for(self, recorded_at: datetime) -> Path:
        return self._trace_directory() / f"{recorded_at.astimezone(UTC):%Y-%m-%d}.jsonl"

    def _trace_directory(self) -> Path:
        data_directory = self._policy.data_dir.resolve()
        trace_directory = (data_directory / TRACE_DIRECTORY_NAME).resolve()
        try:
            trace_directory.relative_to(data_directory)
        except ValueError as error:
            raise ValueError("trace directory must stay under DATA_DIR") from error
        return trace_directory


def trace_policy_from_settings() -> TracePolicy:
    """从项目应用配置构造策略，不读取或记录任何环境变量值。"""

    from app.core.config import settings

    return TracePolicy(
        data_dir=settings.RAG_TRACE_DIR or settings.DATA_DIR,
        store_query=settings.RAG_TRACE_STORE_QUERY,
        store_text=settings.RAG_TRACE_STORE_TEXT,
        max_candidates=settings.RAG_TRACE_MAX_CANDIDATES,
        max_text_chars=settings.RAG_TRACE_MAX_TEXT_CHARS,
        retention_days=settings.RAG_TRACE_RETENTION_DAYS,
    )


def trace_store_from_settings() -> TraceStore | None:
    """仅在项目 feature flag 启用时提供持久化仓库。"""

    from app.core.config import settings

    if not settings.RAG_TRACE_ENABLED:
        return None
    return TraceStore(trace_policy_from_settings())


def sanitize_trace(trace: RetrievalTrace, policy: TracePolicy) -> RetrievalTrace:
    """返回可持久化副本，默认不保留查询、正文、密钥或绝对路径。"""

    plan = trace.query_plan.model_copy(
        update={"query": trace.query_plan.query if policy.store_query else NOT_PERSISTED}
    )
    answer = _sanitize_answer(trace.answer, policy)
    return trace.model_copy(
        update={
            "query_original": trace.query_original if policy.store_query else None,
            "query_plan": plan,
            "filters": _redact_mapping(trace.filters),
            "dense_candidates": _limit_evidence(trace.dense_candidates, policy),
            "sparse_candidates": _limit_evidence(trace.sparse_candidates, policy),
            "rrf_candidates": _limit_evidence(trace.rrf_candidates, policy),
            "reranked_candidates": _limit_evidence(trace.reranked_candidates, policy),
            "selected_evidence": _sanitize_evidence_set(trace.selected_evidence, policy),
            "rejected_evidence": _limit_evidence(trace.rejected_evidence, policy),
            "answer": answer,
            "citations": [_sanitize_citation(item) for item in trace.citations],
            "candidates": _limit_candidates(trace.candidates, policy),
            "evidence": _sanitize_evidence_set(trace.evidence, policy),
        }
    )


def replay_candidate_ids(trace: RetrievalTrace) -> list[str]:
    """在固定索引/配置下给出稳定的候选顺序，供可重放检索核对。"""

    candidates = (
        trace.reranked_candidates
        or trace.rrf_candidates
        or trace.selected_evidence.evidence
        or trace.dense_candidates + trace.sparse_candidates
    )
    ordered = sorted(candidates, key=lambda item: (item.rank, item.chunk_id))
    return list(dict.fromkeys(item.chunk_id for item in ordered))


def _limit_evidence(
    candidates: list[RankedEvidence], policy: TracePolicy
) -> list[RankedEvidence]:
    return [_sanitize_evidence(item, policy) for item in candidates[: policy.max_candidates]]


def _limit_candidates(
    candidates: list[RetrievalCandidate], policy: TracePolicy
) -> list[RetrievalCandidate]:
    return [
        item.model_copy(
            update={
                "source_path": _safe_source_path(item.source_path),
                "text_original": _limited_text(item.text_original, policy),
            }
        )
        for item in candidates[: policy.max_candidates]
    ]


def _sanitize_evidence(item: RankedEvidence, policy: TracePolicy) -> RankedEvidence:
    return item.model_copy(
        update={
            "source_path": _safe_source_path(item.source_path),
            "text_original": _limited_text(item.text_original, policy),
        }
    )


def _sanitize_evidence_set(evidence: EvidenceSet, policy: TracePolicy) -> EvidenceSet:
    return evidence.model_copy(update={"evidence": _limit_evidence(evidence.evidence, policy)})


def _sanitize_answer(answer: GroundedAnswer | None, policy: TracePolicy) -> GroundedAnswer | None:
    if answer is None:
        return None
    return answer.model_copy(
        update={
            "answer": _limited_text(answer.answer, policy),
            "citations": [_sanitize_citation(item) for item in answer.citations],
        }
    )


def _sanitize_citation(citation: GroundedCitation) -> GroundedCitation:
    return citation.model_copy(update={"source_path": _safe_source_path(citation.source_path)})


def _limited_text(value: str, policy: TracePolicy) -> str:
    if not policy.store_text:
        return ""
    return value[: policy.max_text_chars]


def _safe_source_path(source_path: str) -> str:
    """只保留文件名，避免轨迹和错误输出泄漏本机绝对路径。"""

    return Path(source_path.replace("\\", "/")).name


def _redact_mapping(values: dict[str, object]) -> dict[str, object]:
    redacted: dict[str, object] = {}
    for key, value in values.items():
        if key.lower().replace("-", "_") in SENSITIVE_KEYS:
            redacted[key] = REDACTED
        elif isinstance(value, dict):
            redacted[key] = _redact_mapping(value)
        elif isinstance(value, list):
            redacted[key] = [
                _redact_mapping(item) if isinstance(item, dict) else item for item in value
            ]
        else:
            redacted[key] = value
    return redacted
