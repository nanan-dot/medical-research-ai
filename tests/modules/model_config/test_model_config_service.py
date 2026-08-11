import pytest
from cryptography.fernet import Fernet

from app.common.exceptions import ConflictError
from app.core.security import SecretCipher
from app.integrations.ollama.exceptions import OllamaConfigurationError
from app.modules.model_config.schema import ModelConfigCreate
from app.modules.model_config.service import ModelConfigService


def cipher():
    return SecretCipher(Fernet.generate_key().decode())


def cloud(**changes):
    values = {
        "deployment_mode": "cloud",
        "provider": "openai",
        "api_base": "https://api.example/v1",
        "api_key": "secret-value",
        "model_name": "model",
        "allow_cloud_content": True,
        "is_default": False,
    }
    values.update(changes)
    return ModelConfigCreate(**values)


def local(**changes):
    values = {
        "deployment_mode": "local",
        "provider": "ollama",
        "api_base": "http://127.0.0.1:11434",
        "model_name": "qwen3:4b",
        "allow_cloud_content": False,
        "is_default": False,
    }
    values.update(changes)
    return ModelConfigCreate(**values)


@pytest.mark.asyncio
async def test_cloud_key_is_encrypted_masked_and_never_returned(session):
    service = ModelConfigService(session, cipher=cipher())
    result = await service.create(cloud())
    entity = await service.get(result.id)
    assert "secret-value" not in entity.encrypted_api_key
    assert (
        result.api_key_masked == "••••••••"
        and "secret-value" not in result.model_dump_json()
    )


@pytest.mark.asyncio
async def test_local_config_and_default_are_supported(session):
    service = ModelConfigService(session, cipher=cipher())
    first = await service.create(local(is_default=True))
    second = await service.create(local(model_name="other", is_default=True))
    listed = await service.list()
    assert first.id != second.id and [
        item.id for item in listed if item.is_default
    ] == [second.id]


@pytest.mark.asyncio
async def test_cloud_authorization_and_local_ssrf_are_rejected(session):
    with pytest.raises(ValueError):
        cloud(allow_cloud_content=False)
    request = ModelConfigCreate(
        deployment_mode="local",
        provider="ollama",
        api_base="http://10.0.0.2:11434",
        model_name="x",
    )
    with pytest.raises(OllamaConfigurationError):
        await ModelConfigService(session, cipher=cipher()).create(request)


def test_encryption_rotation_and_wrong_key():
    old = Fernet.generate_key().decode()
    new = Fernet.generate_key().decode()
    token = SecretCipher(old).encrypt("value")
    rotated = SecretCipher(f"{new},{old}").rotate(token)
    assert SecretCipher(new).decrypt(rotated) == "value"
    with pytest.raises(ConflictError):
        SecretCipher(Fernet.generate_key().decode()).decrypt(token)


@pytest.mark.asyncio
async def test_connection_success_failure_and_cost_acknowledgement(session):
    calls = []

    async def ok(entity, key):
        calls.append((entity.provider, key))

    service = ModelConfigService(session, cipher=cipher(), tester=ok)
    config = await service.create(cloud())
    with pytest.raises(ConflictError, match="cost"):
        await service.test(config.id, False)
    assert (await service.test(config.id, True)).success and calls[0][
        1
    ] == "secret-value"

    async def fail(entity, key):
        raise ValueError("bad endpoint secret-value")

    service.tester = fail
    with pytest.raises(ConflictError, match="failed"):
        await service.test(config.id, True)
