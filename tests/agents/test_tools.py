import pytest

from app.agents.tools import ServiceTool, ToolRegistry, ToolSpec


def test_registered_tool_invokes_injected_service_only():
    tool = ServiceTool(ToolSpec("citation_check", "check", 10, True), lambda payload: {"ok": payload["id"]})
    registry = ToolRegistry(); registry.register(tool)
    assert registry.get("citation_check").run({"id": 1}, idempotency_key="k") == {"ok": 1}
def test_rejects_missing_key_and_duplicate_name():
    tool = ServiceTool(ToolSpec("x", "x", 1, True), lambda _: {})
    with pytest.raises(ValueError): tool.run({}, idempotency_key="")
    registry = ToolRegistry(); registry.register(tool)
    with pytest.raises(ValueError): registry.register(tool)
