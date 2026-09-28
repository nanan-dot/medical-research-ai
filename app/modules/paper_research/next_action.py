"""Deterministic, side-effect-free continue-work decisions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ActionDecision:
    kind: str
    title: str
    description: str
    reason_codes: list[str]
    target: dict[str, object] | None
    is_available: bool
    unavailable_reason: str | None = None


def decide_next_action(
    *,
    pending_fields: int,
    analysis_status: str | None,
    reading_status: str,
    can_read: bool,
    can_analyze: bool,
    reader_target: dict[str, object] | None,
    section: str | None,
    item_id: int,
) -> ActionDecision:
    """Apply the published priority table and return an honest entry capability."""
    if pending_fields:
        return ActionDecision(
            "confirm_analysis",
            "确认分析字段",
            "处理待确认的分析字段",
            ["pending_confirmation"],
            {"item_id": item_id},
            True,
        )
    if analysis_status in {"pending", "analyzing"}:
        return ActionDecision(
            "continue_analysis",
            "继续论文分析",
            "继续未完成的分析任务",
            ["analysis_in_progress"],
            {"item_id": item_id},
            can_analyze,
            None if can_analyze else "analysis_unavailable",
        )
    if reading_status == "reading":
        if not can_read:
            return ActionDecision(
                "continue_reading",
                "继续阅读",
                "全文资源当前不可用",
                ["reading_incomplete", "resource_unavailable"],
                None,
                False,
                "reader_unavailable",
            )
        if reader_target:
            return ActionDecision(
                "continue_reading",
                "继续阅读",
                "从最近有效阅读位置继续",
                ["reading_incomplete", "exact_resume"],
                reader_target,
                True,
            )
        return ActionDecision(
            "continue_reading",
            "继续阅读",
            "从已知章节继续",
            ["reading_incomplete", "section_resume"],
            {"item_id": item_id, "section": section}
            if section
            else {"item_id": item_id},
            True,
        )
    if reading_status == "unread" and can_read:
        return ActionDecision(
            "start_reading",
            "开始阅读",
            "全文已可用，尚未开始阅读",
            ["readable_unstarted"],
            {"item_id": item_id},
            True,
        )
    if analysis_status is None and can_analyze:
        return ActionDecision(
            "start_analysis",
            "开始论文分析",
            "可以创建分析任务",
            ["analyzable_unstarted"],
            {"item_id": item_id},
            True,
        )
    return ActionDecision(
        "unavailable",
        "暂无法继续",
        "没有可安全执行的下一步",
        ["no_available_entry"],
        None,
        False,
        "no_available_entry",
    )
