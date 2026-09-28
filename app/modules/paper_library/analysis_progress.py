"""论文分析任务集合的持久化快照与只读投影。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.modules.paper_analysis.model import PaperAnalysis


@dataclass(frozen=True, slots=True)
class AnalysisProgress:
    completed: int
    total: int


def encode_task_names(task_names: tuple[str, ...] | list[str]) -> str:
    """把当前模板的任务集合固化到分析记录，避免未来模板变化改写历史。"""
    return json.dumps(list(dict.fromkeys(task_names)), ensure_ascii=False)


def decode_task_names(raw: str | None) -> tuple[str, ...] | None:
    if raw is None:
        return None
    try:
        values = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
        return None
    normalized = tuple(dict.fromkeys(item for item in values if item))
    return normalized


def project_analysis_progress(analysis: PaperAnalysis | None) -> AnalysisProgress | None:
    """只信任同一次分析持久化的任务快照；历史数据无法解释时返回未知。"""
    if analysis is None or not analysis.task_set_version:
        return None
    tasks = decode_task_names(analysis.task_names_json)
    completed = decode_task_names(analysis.completed_task_names_json)
    if not tasks or completed is None:
        return None
    task_set = set(tasks)
    if not set(completed).issubset(task_set):
        return None
    return AnalysisProgress(completed=len(completed), total=len(tasks))
