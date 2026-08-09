"""模拟导师模型路由的隐私边界与结构化输出测试。"""

from datetime import UTC, datetime

import pytest

from app.common.exceptions import ConflictError, TemporarilyUnavailableError
from app.modules.advisor_workflow.mock_reviewer import MOCK_WARNING, MockReviewGenerator
from app.modules.model_config.model import ModelConfig


class _ScalarResult:
    def __init__(self, value: ModelConfig | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> ModelConfig | None:
        return self._value


class _Session:
    def __init__(self, default: ModelConfig | None = None) -> None:
        self.default = default

    async def get(self, _model, config_id: int):
        if self.default is not None and self.default.id == config_id:
            return self.default
        return None

    async def execute(self, _statement) -> _ScalarResult:
        return _ScalarResult(self.default)


def _config(
    provider: str,
    *,
    config_id: int = 1,
    allow_cloud_content: bool = False,
) -> ModelConfig:
    now = datetime.now(UTC)
    return ModelConfig(
        id=config_id,
        deployment_mode="local" if provider == "ollama" else "cloud",
        provider=provider,
        api_base="http://127.0.0.1:11434/v1"
        if provider == "ollama"
        else "https://example.test/v1",
        encrypted_api_key=None,
        model_name="review-model",
        is_default=True,
        allow_cloud_content=allow_cloud_content,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_default_mock_review_route_requires_local_ollama() -> None:
    generator = MockReviewGenerator(_Session(_config("openai")))  # type: ignore[arg-type]

    with pytest.raises(ConflictError, match="requires local Ollama"):
        await generator._resolve_config(None, None)


@pytest.mark.asyncio
async def test_explicit_allowed_cloud_route_is_accepted() -> None:
    config = _config("openai", allow_cloud_content=True)
    generator = MockReviewGenerator(_Session(config))  # type: ignore[arg-type]

    selected = await generator._resolve_config("openai", config.id)

    assert selected is config


@pytest.mark.asyncio
async def test_cloud_route_cannot_be_selected_implicitly() -> None:
    config = _config("openai", allow_cloud_content=True)
    generator = MockReviewGenerator(_Session(config))  # type: ignore[arg-type]

    with pytest.raises(ConflictError, match="requires local Ollama"):
        await generator._resolve_config(None, config.id)


def test_structured_mock_review_is_validated_and_labelled() -> None:
    payload = MockReviewGenerator._parse(
        """{
          "decision": "revise",
          "summary": "The scope needs refinement.",
          "points": [{
            "field_name": "gap",
            "topic": "Evidence gap",
            "content": "Validate the gap with a reproducible search.",
            "severity": "major"
          }],
          "literature_gaps": [],
          "experiment_conditions": []
        }"""
    )

    assert payload.summary.startswith(MOCK_WARNING)
    assert payload.decision == "revise"


def test_invalid_model_output_is_rejected() -> None:
    with pytest.raises(TemporarilyUnavailableError, match="invalid structured output"):
        MockReviewGenerator._parse("not json")
