"""Agent 执行资源限制的纯规则。"""

from dataclasses import dataclass


class LimitExceededError(ValueError):
    """表示工作流必须进入明确终态的限制违规。"""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AgentLimits:
    """单次运行的步骤、工具、资源和时长上限。"""

    max_steps: int = 12
    max_tool_calls: int = 8
    max_resource_units: int = 100
    total_timeout_seconds: float = 300.0

    def assert_allowed(
        self, *, step_count: int, tool_calls: int, resource_units: int, elapsed_seconds: float
    ) -> None:
        """验证所有上限，超限时返回稳定错误代码。"""

        if step_count > self.max_steps:
            raise LimitExceededError("maximum_workflow_steps_reached")
        if tool_calls > self.max_tool_calls:
            raise LimitExceededError("maximum_tool_calls_reached")
        if resource_units > self.max_resource_units:
            raise LimitExceededError("maximum_resource_units_reached")
        if elapsed_seconds > self.total_timeout_seconds:
            raise LimitExceededError("workflow_timeout_reached")
