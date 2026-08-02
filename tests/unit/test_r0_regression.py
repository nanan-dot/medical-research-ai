"""Focused R0 failure-mode and error-code regression tests."""

from pathlib import Path

import httpx
import pytest

from app.cli.r0_demo import DemoError, _validate_pdf
from app.integrations.llm import ChatMessage
from app.integrations.llm.client import LLMClient
from app.integrations.llm.exceptions import (
    LLMAuthenticationError,
    LLMModelNotFoundError,
    LLMTimeoutError,
)
from app.integrations.ollama.exceptions import (
    OllamaModelNotFoundError,
    OllamaServiceUnavailableError,
)
from app.integrations.paperqa2.exceptions import (
    PaperQA2IndexCorruptError,
    PaperQA2OperationError,
    PaperQA2ResponseError,
)
from tests.unit.test_llm_client import make_client as make_llm_client


def test_non_pdf_extension_and_fake_pdf_are_rejected(tmp_path: Path):
    text = tmp_path / "paper.txt"
    text.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(DemoError, match=".pdf extension"):
        _validate_pdf(text)

    fake = tmp_path / "paper.pdf"
    fake.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(DemoError, match="not a valid PDF"):
        _validate_pdf(fake)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected"),
    ((401, LLMAuthenticationError), (404, LLMModelNotFoundError)),
)
async def test_wrong_cloud_key_and_model_have_stable_errors(status_code, expected):
    client: LLMClient = make_llm_client(lambda _: httpx.Response(status_code, json={}))
    with pytest.raises(expected) as captured:
        await client.chat([ChatMessage(role="user", content="fixed")])
    await client._http_client.aclose()
    assert captured.value.code in {"llm_authentication_error", "llm_model_not_found"}


@pytest.mark.asyncio
async def test_cloud_timeout_has_stable_error():
    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("mock timeout", request=request)

    client = make_llm_client(timeout)
    with pytest.raises(LLMTimeoutError) as captured:
        await client.chat([ChatMessage(role="user", content="fixed")])
    await client._http_client.aclose()
    assert captured.value.code == "llm_timeout_error"


def test_required_error_code_inventory_is_stable():
    assert {
        OllamaServiceUnavailableError.code,
        OllamaModelNotFoundError.code,
        PaperQA2OperationError.code,
        PaperQA2IndexCorruptError.code,
        PaperQA2ResponseError.code,
    } == {
        "ollama_service_unavailable",
        "ollama_model_not_found",
        "paperqa2_operation_error",
        "paperqa2_index_corrupt",
        "paperqa2_response_error",
    }


def test_windows_permission_equivalent_uses_non_directory_parent(tmp_path: Path):
    """A file-as-parent is deterministic where chmod is advisory on Windows."""
    parent = tmp_path / "paperqa_index"
    parent.write_text("blocks directory creation", encoding="utf-8")
    with pytest.raises((FileExistsError, NotADirectoryError, OSError)):
        (parent / "index").mkdir(parents=True)
