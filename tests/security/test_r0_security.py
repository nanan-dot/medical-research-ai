"""Security checks that never call paid or external services."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.paperqa2.client import PaperQA2Client
from app.integrations.paperqa2.exceptions import PaperQA2OperationError
from app.integrations.paperqa2.schemas import PaperQA2Config

REPOSITORY = Path(__file__).resolve().parents[2]
SENTINEL_SECRET = "r0-security-sentinel-not-a-real-key"


def _git(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPOSITORY,
        input=input_text,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )


def test_sensitive_and_generated_paths_are_ignored():
    candidates = (
        ".env",
        ".env.local",
        "data/security-test.pdf",
        "data/r0_demo/result.json",
        "uploads/unpublished.pdf",
        "logs/application.log",
        "paperqa_index/test.index",
    )
    for candidate in candidates:
        result = _git("check-ignore", "-q", "--", candidate)
        assert result.returncode == 0, candidate


def test_no_sensitive_runtime_files_are_tracked():
    result = _git("ls-files", "-z")
    assert result.returncode == 0
    tracked = [Path(value) for value in result.stdout.split("\0") if value]
    forbidden = [
        path
        for path in tracked
        if path.name in {".env", ".env.local"}
        or path.suffix.lower() in {".pdf", ".db", ".sqlite3", ".log"}
        or (path.parts and path.parts[0] in {"data", "uploads"})
    ]
    assert forbidden == []


def test_configured_real_keys_do_not_appear_in_tracked_files():
    app_settings = Settings()
    secrets = [
        value
        for value in (app_settings.OPENAI_API_KEY, app_settings.OPENROUTER_API_KEY)
        if value
    ]
    if not secrets:
        pytest.skip("no local cloud key is configured")

    tracked_result = _git("ls-files", "-z")
    tracked_paths = [value for value in tracked_result.stdout.split("\0") if value]
    leaks: list[str] = []
    for relative in tracked_paths:
        tracked_path = REPOSITORY / relative
        # 未提交删除的 tracked 文件仍会出现在 git ls-files 中，但它已不属于当前
        # 工作区内容，也不可能泄露当前密钥；安全扫描应跳过，而不是中断整套验证。
        if not tracked_path.is_file():
            continue
        content = tracked_path.read_bytes()
        for secret in secrets:
            if secret.encode() in content:
                leaks.append(relative)
    assert leaks == []


class _ExplodingBackend:
    def index_documents(self, documents, index_id, rebuild=False):
        raise RuntimeError(SENTINEL_SECRET)

    def ask(self, index_id, question):
        raise RuntimeError(SENTINEL_SECRET)


@pytest.mark.asyncio
async def test_paperqa_configuration_and_errors_do_not_expose_key(tmp_path: Path):
    config = PaperQA2Config(
        version="2026.3.18",
        provider="openai",
        api_base_url="https://example.test/v1",
        api_key=SecretStr(SENTINEL_SECRET),
        llm_model="mock-model",
        embedding_model="nomic-embed-text",
    )
    assert SENTINEL_SECRET not in repr(config)
    client = PaperQA2Client(config, _ExplodingBackend())
    pdf = tmp_path / "public.pdf"
    pdf.write_bytes(b"%PDF-test")

    with pytest.raises(PaperQA2OperationError) as captured:
        await client.index_documents([pdf])
    assert SENTINEL_SECRET not in captured.value.message
    assert SENTINEL_SECRET not in str(captured.value)
