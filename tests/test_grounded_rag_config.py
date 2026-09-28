import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_wp7_defaults_to_paperqa() -> None:
    settings = Settings()
    assert settings.GROUNDED_RAG_MODE == "paperqa"
    assert settings.GROUNDED_RAG_ENABLED is False


def test_wp7_rejects_unknown_grounded_mode() -> None:
    with pytest.raises(ValidationError):
        Settings(GROUNDED_RAG_MODE="unknown")
