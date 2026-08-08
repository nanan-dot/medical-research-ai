"""研究条件的无副作用校验规则。"""

from collections.abc import Mapping

FEASIBLE_RESEARCH_TYPES = ("clinical", "animal", "cell", "bioinformatics")


class ResearchConditionsValidationError(ValueError):
    """表示可安全返回给用户的研究条件输入错误。"""


def validate_field_state(*, known: bool, source: str, value: object | None) -> None:
    """校验字段值、已知标记与来源的一致性。"""
    if known and source != "user":
        raise ResearchConditionsValidationError("known=true fields must use source=user")
    if not known and source != "unknown":
        raise ResearchConditionsValidationError("known=false fields must use source=unknown")
    if not known and value is not None:
        raise ResearchConditionsValidationError("unknown fields must not contain a value")
    if known and _is_blank_value(value):
        raise ResearchConditionsValidationError("known=true fields require a non-empty value")


def validate_feasible_research_types(values: list[str]) -> None:
    """校验可开展研究类型，非法值附带白名单以支持前端提示。"""
    illegal_values = sorted(set(values).difference(FEASIBLE_RESEARCH_TYPES))
    if illegal_values:
        allowed_values = ", ".join(FEASIBLE_RESEARCH_TYPES)
        raise ResearchConditionsValidationError(
            f"invalid feasible research types: {', '.join(illegal_values)}; "
            f"allowed values: {allowed_values}"
        )


def validate_nonempty_minimal_input(
    conditions: Mapping[str, object | None],
) -> None:
    """要求至少提供一个新生最小输入字段，未知选择不计为已提供内容。"""
    minimal_fields = {
        "specialty",
        "advisor_direction",
        "interest_topic",
        "existing_papers",
        "feasible_research_types",
    }
    for field_name in minimal_fields:
        condition = conditions.get(field_name)
        if condition is None:
            continue
        known = _condition_known(condition)
        value = _condition_value(condition)
        if known and not _is_blank_value(value):
            return
    raise ResearchConditionsValidationError(
        "at least one minimal input field with known=true is required"
    )


def exclude_unknown_fields(
    conditions: Mapping[str, object | None],
) -> dict[str, object]:
    """返回仅含用户明确提供字段的候选方向输入，阻止未知字段被模型补全。"""
    return {
        field_name: _condition_value(condition)
        for field_name, condition in conditions.items()
        if condition is not None and _condition_known(condition)
    }


def _is_blank_value(value: object | None) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    return False


def _condition_known(condition: object) -> bool:
    if isinstance(condition, Mapping):
        return bool(condition.get("known", False))
    return bool(getattr(condition, "known", False))


def _condition_value(condition: object) -> object | None:
    if isinstance(condition, Mapping):
        return condition.get("value")
    return getattr(condition, "value", None)
