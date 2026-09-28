"""Agent-independent tool contracts; tools never access persistence directly."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    timeout_seconds: float
    idempotent: bool


class ServiceTool:
    def __init__(
        self, spec: ToolSpec, invoke: Callable[[dict[str, object]], dict[str, object]]
    ) -> None:
        self.spec, self._invoke = spec, invoke

    def run(
        self, payload: dict[str, object], *, idempotency_key: str
    ) -> dict[str, object]:
        if not idempotency_key:
            raise ValueError("idempotency_key is required")
        return self._invoke(payload)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ServiceTool] = {}

    def register(self, tool: ServiceTool) -> None:
        if tool.spec.name in self._tools:
            raise ValueError("duplicate tool name")
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> ServiceTool:
        return self._tools[name]
