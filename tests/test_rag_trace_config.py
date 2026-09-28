import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.rag.trace import trace_policy_from_settings, trace_store_from_settings


def test_wp8_trace_defaults_minimize_content_collection() -> None:
    settings = Settings(_env_file=None)

    assert settings.RAG_TRACE_ENABLED is False
    assert settings.RAG_TRACE_STORE_QUERY is False
    assert settings.RAG_TRACE_STORE_TEXT is False


def test_wp8_trace_directory_must_stay_under_data_dir(tmp_path) -> None:
    with pytest.raises(ValidationError, match="RAG_TRACE_DIR must stay under DATA_DIR"):
        Settings(
            _env_file=None,
            DATA_DIR=tmp_path / "data",
            RAG_TRACE_DIR=tmp_path / "outside",
        )


def test_wp8_trace_policy_uses_project_settings(monkeypatch, tmp_path) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "DATA_DIR", tmp_path)
    policy = trace_policy_from_settings()

    assert policy.data_dir == tmp_path
    assert policy.store_query is False and policy.store_text is False


def test_wp8_trace_store_is_disabled_by_default(monkeypatch) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "RAG_TRACE_ENABLED", False)

    assert trace_store_from_settings() is None
