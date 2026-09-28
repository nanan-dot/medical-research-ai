"""Shared test fixtures supplied by module-level API test helpers."""

import pytest

from app.modules.recommendation.v5_scheduler import RecommendationScheduler

pytest_plugins = [
    "tests.modules.document.test_api",
    "tests.modules.knowledge_source.test_api",
    "tests.modules.library.library_test_support",
]


@pytest.fixture(autouse=True)
def disable_lifespan_recovery_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep app-lifespan background recovery out of isolated API test databases."""

    async def stop_recovery_loop() -> None:
        return None

    monkeypatch.setattr(RecommendationScheduler, "start_recovery_loop", lambda: None)
    monkeypatch.setattr(RecommendationScheduler, "stop_recovery_loop", stop_recovery_loop)
