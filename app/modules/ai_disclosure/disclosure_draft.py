"""可编辑披露草稿模板。"""

from collections.abc import Iterable

from app.modules.ai_disclosure.schema import AIUsageEventRead

_NOTICE = (
    "AI 生成内容仅供辅助，您对最终内容负责；AI 不能作为作者；"
    "学校/期刊可能要求披露 AI 使用；未发表材料请注意保密。"
)
_DISCLAIMER = "各期刊要求不同，请按目标期刊要求调整，不代表适用于所有期刊。"


def build_disclosure_draft(
    events: Iterable[AIUsageEventRead],
    *,
    confidential: bool,
    include_notice: bool = True,
) -> str:
    lines = ([_NOTICE] if include_notice else []) + [_DISCLAIMER, "", "AI 使用说明："]
    event_list = list(events)
    if not event_list:
        lines.append(
            "该项目无 AI 使用记录。输入范围：[confidential]"
            if confidential
            else "该项目无 AI 使用记录。"
        )
    for event in event_list:
        scope = "[confidential]" if confidential else event.input_scope
        lines.append(
            f"- 模型：{event.model_name} {event.model_version}；日期：{event.created_at.date()}；"
            f"用途：{event.purpose}；输入范围：{scope}；人工修改：{event.human_edited}。"
        )
    return "\n".join(lines)
