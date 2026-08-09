"""Resumable evaluation runner with immutable per-question records."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Literal

from app.modules.evaluation.dataset import EvaluationQuestion

RunStatus = Literal["pending", "running", "completed", "cancelled", "failed"]


@dataclass(frozen=True)
class EvaluationConfig:
    """Reproducibility snapshot; callers must provide all runtime choices."""
    dataset_version: str
    retriever_config: dict[str, object]
    model_config: dict[str, object]
    prompt_version: str


@dataclass(frozen=True)
class QuestionRun:
    question_id: str
    status: Literal["completed", "failed"]
    raw_output: str | None
    elapsed_ms: int
    error: str | None = None


@dataclass
class EvaluationRun:
    config: EvaluationConfig
    status: RunStatus = "pending"
    records: list[QuestionRun] = field(default_factory=list)


QuestionExecutor = Callable[[EvaluationQuestion], str]


def execute(run: EvaluationRun, questions: list[EvaluationQuestion], executor: QuestionExecutor, *, cancel_requested: Callable[[], bool] | None = None) -> EvaluationRun:
    """Run unprocessed questions; individual failures are retained and do not stop a batch."""
    if run.status in {"completed", "cancelled"}:
        return run
    # 仅已完成记录跳过；failed 记录允许在恢复执行时重试（不永久丢弃失败题目）。
    completed_ids = {
        record.question_id for record in run.records if record.status == "completed"
    }
    run.status = "running"
    for question in questions:
        if question.question_id in completed_ids:
            continue
        if cancel_requested is not None and cancel_requested():
            run.status = "cancelled"
            return run
        started = perf_counter()
        try:
            output = executor(question)
            run.records.append(QuestionRun(question.question_id, "completed", output, round((perf_counter() - started) * 1000)))
        except Exception as error:  # noqa: BLE001 — 任何执行异常都收敛为 failed，避免状态卡死在 running
            run.records.append(QuestionRun(question.question_id, "failed", None, round((perf_counter() - started) * 1000), str(error)))
    run.status = "completed"
    return run
