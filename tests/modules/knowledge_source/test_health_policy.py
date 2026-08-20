"""Acceptance tests for one health policy shared by read and query operations."""

from app.modules.knowledge_source.health import health_status


def test_health_priority_is_deterministic() -> None:
    """AC-05/12: pause wins, followed by source availability and document failures."""
    assert health_status(False, "unavailable", 8, True) == "paused"
    assert health_status(True, "unavailable", 0, False) == "unavailable"
    assert health_status(True, "scanning", 0, False) == "syncing"
    assert health_status(True, "completed_with_errors", 0, False) == "needs_attention"
    assert health_status(True, "completed", 2, False) == "needs_attention"
    assert health_status(True, "completed", 0, False) == "ready"
