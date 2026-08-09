"""本地 Agent 轨迹摘要与脱敏导出。"""

import re
from dataclasses import asdict, dataclass
from time import time

MAX_SUMMARY_LENGTH = 240
_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|token|password)\s*[:=]\s*\S+|sk-[A-Za-z0-9_-]+")


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
    approval: str | None = None
    created_at: float = 0.0

    def to_dict(self) -> dict[str, object]:
        """转换为 JSON 安全的导出对象。"""

        data = asdict(self)
        data["source_ids"] = list(self.source_ids)
        return data


def create_event(run_id: str, node: str, before: object, after: object) -> TraceEvent:
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
    )
