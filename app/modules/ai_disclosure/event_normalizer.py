"""隐私友好的 AI 使用事件归一化。"""

from collections.abc import Mapping

from app.modules.ai_disclosure.schema import AIUsageEventCreate, Purpose


def normalize_event(
    *,
    model_name: str,
    model_version: str,
    purpose: Purpose,
    input_scope: Mapping[str, object] | str,
    output_version: str,
    human_edited: bool,
    is_cloud: bool,
) -> AIUsageEventCreate:
    if isinstance(input_scope, str):
        scope = "用户材料"
    else:
        scope = _scope_summary(input_scope)
    return AIUsageEventCreate(
        model_name=model_name,
        model_version=model_version,
        purpose=purpose,
        input_scope=scope,
        output_version=output_version,
        human_edited=human_edited,
        is_cloud=is_cloud,
    )


def _scope_summary(scope: Mapping[str, object]) -> str:
    parts: list[str] = []
    labels = (
        ("papers", "篇文献"),
        ("matrices", "个证据矩阵"),
        ("user_notes", "段用户笔记"),
    )
    for key, label in labels:
        value = scope.get(key)
        if isinstance(value, int) and value >= 0:
            parts.append(f"{value} {label}")
    return "、".join(parts) if parts else "用户材料"
