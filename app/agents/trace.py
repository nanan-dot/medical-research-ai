"""本地 Agent 轨迹摘要与脱敏导出。"""

import re
from dataclasses import asdict, dataclass
from time import time

from pydantic import TypeAdapter

MAX_SUMMARY_LENGTH = 240
# 脱敏覆盖三种形态：
#  1) JSON 风格键值（带可选引号键 + 引号/非引号值）："api_key": "secret" / token = abc
#  2) sk- 前缀的 OpenAI 风格密钥
#  3) 常见密钥键名（authorization / secret / credential）
_SECRET_PATTERN = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|token|password|secret|authorization|credential)"
    r"[\"']?\s*[:=]\s*(?:[\"'][^\"']*[\"']|[^\"'\s,}]+))"
    r"|sk-[A-Za-z0-9_-]+"
)


def summarize(value: object) -> str:
    """生成截断且脱敏的调试摘要，不保存原始敏感正文。"""

    text = str(value)
    text = _SECRET_PATTERN.sub("[REDACTED]", text)
    return text[:MAX_SUMMARY_LENGTH]


@dataclass(frozen=True)
class TraceEvent:
    run_id: str
    node: str
    status: str
    input_summary: str
    output_summary: str
    duration_ms: int
    error: str | None = None
    tool: str | None = None
    model: str | None = None
    source_ids: tuple[int, ...] = ()
    trace_id: str | None = None
    sources: tuple[dict[str, object], ...] = ()
    approval: str | None = None
    created_at: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """转换为 JSON 安全的导出对象。"""

        data = asdict(self)
        data["source_ids"] = list(self.source_ids)
        data["sources"] = list(self.sources)
        return data

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "TraceEvent":
        """从 JSON 审计记录恢复不可变事件。"""
        restored = dict(payload)
        restored["source_ids"] = TypeAdapter(tuple[int, ...]).validate_python(
            restored.get("source_ids", [])
        )
        restored["sources"] = TypeAdapter(tuple[dict[str, object], ...]).validate_python(
            restored.get("sources", [])
        )
        return cls(**restored)  # type: ignore[arg-type]


def create_event(
    run_id: str,
    node: str,
    before: object,
    after: object,
    *,
    trace_id: str | None = None,
    sources: list[dict[str, object]] | None = None,
    approval: str | None = None,
) -> TraceEvent:
    """创建本地轨迹事件；耗时以调用边界的最小可观测值记录。"""

    started = time()
    return TraceEvent(
        run_id=run_id,
        node=node,
        status="completed",
        input_summary=summarize(before),
        output_summary=summarize(after),
        duration_ms=max(0, int((time() - started) * 1000)),
        created_at=time(),
        trace_id=trace_id,
        sources=tuple(sources or []),
        approval=approval,
    )
