"""PaperQA2 adapter tests without importing or calling the external package."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.integrations.paperqa2.client import PaperQA2Client, _BackendIndexResult
from app.integrations.paperqa2.exceptions import (
    PaperQA2ConfigurationError,
    PaperQA2IndexCorruptError,
    PaperQA2OperationError,
    PaperQA2ResponseError,
)
from app.integrations.paperqa2.factory import create_paperqa2_client
from app.integrations.paperqa2.factory import _OfficialPaperQA2Backend
from app.integrations.paperqa2.schemas import PaperQA2Config


class FakeBackend:
    def __init__(self, session=None, error: Exception | None = None):
        self.session = session
        self.error = error
        self.index_ids: set[str] = set()
        self.thread_ids: list[int] = []

    def index_documents(self, documents, index_id, rebuild=False):
        self.thread_ids.append(threading.get_ident())
        if self.error:
            raise self.error
        reused = index_id in self.index_ids and not rebuild
        self.index_ids.add(index_id)
        return _BackendIndexResult(index_id, len(documents), reused)

    def ask(self, index_id, question):
        self.thread_ids.append(threading.get_ident())
        if self.error:
            raise self.error
        return self.session


def make_client(backend: FakeBackend) -> PaperQA2Client:
    return PaperQA2Client(
        PaperQA2Config(
            version="2026.3.18",
            provider="ollama",
            api_base_url="http://127.0.0.1:11434",
            llm_model="qwen3:4b",
            embedding_model="nomic-embed-text",
        ),
        backend,
    )


def make_session(*, contexts):
    return SimpleNamespace(
        answer="A grounded answer.", raw_answer="", contexts=contexts
    )


@pytest.mark.asyncio
async def test_raw_answer_and_source_are_converted_without_external_types(
    tmp_path: Path,
):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    document = SimpleNamespace(docname="trial", citation="Journal citation")
    text = SimpleNamespace(
        name="trial pages 11-12",
        doc=document,
        text="Evidence from the paper.",
    )
    backend = FakeBackend(
        make_session(
            contexts=[SimpleNamespace(text=text, context=text.text, score=4.5)]
        )
    )
    client = make_client(backend)

    index = await client.index_documents([pdf])
    answer = await client.ask(index, "What happened?")

    assert answer.model_dump() == {
        "answer": "A grounded answer.",
        "index_id": index.index_id,
        "sources": [
            {
                "source_id": "trial pages 11-12",
                "title": "trial",
                "citation": "Journal citation",
                "page_start": 11,
                "page_end": 12,
                "excerpt": "Evidence from the paper.",
                "score": 4.5,
            }
        ],
    }
    assert type(answer).__module__ == "app.integrations.paperqa2.schemas"


@pytest.mark.asyncio
async def test_missing_page_numbers_remain_none(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    text = SimpleNamespace(
        name="paper chunk unknown", doc=SimpleNamespace(), text="Evidence"
    )
    client = make_client(
        FakeBackend(make_session(contexts=[SimpleNamespace(text=text)]))
    )
    index = await client.index_documents([pdf])

    source = (await client.ask(index, "Question")).sources[0]

    assert source.page_start is None
    assert source.page_end is None
    assert source.title is None
    assert source.citation is None


@pytest.mark.asyncio
async def test_empty_sources_are_valid(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    client = make_client(FakeBackend(make_session(contexts=[])))
    index = await client.index_documents([pdf])
    assert (await client.ask(index, "Question")).sources == []


@pytest.mark.asyncio
async def test_repeat_index_returns_same_reference_and_reused_flag(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    client = make_client(FakeBackend(make_session(contexts=[])))

    first = await client.index_documents([pdf])
    second = await client.index_documents([pdf])
    rebuilt = await client.index_documents([pdf], rebuild=True)

    assert first.index_id == second.index_id
    assert first.reused is False
    assert second.reused is True
    assert rebuilt.index_id == first.index_id
    assert rebuilt.reused is False


@pytest.mark.asyncio
async def test_blocking_backend_runs_outside_event_loop_thread(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    backend = FakeBackend(make_session(contexts=[]))
    event_loop_thread = threading.get_ident()
    client = make_client(backend)

    index = await client.index_documents([pdf])
    await client.ask(index, "Question")

    assert backend.thread_ids
    assert all(thread_id != event_loop_thread for thread_id in backend.thread_ids)


@pytest.mark.asyncio
async def test_external_exception_is_sanitized(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    client = make_client(FakeBackend(error=RuntimeError("secret external payload")))

    with pytest.raises(PaperQA2OperationError) as captured:
        await client.index_documents([pdf])

    assert "secret external payload" not in captured.value.message


@pytest.mark.asyncio
async def test_structured_adapter_error_is_preserved(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    client = make_client(
        FakeBackend(error=PaperQA2IndexCorruptError("Index is corrupted"))
    )
    with pytest.raises(PaperQA2IndexCorruptError):
        await client.index_documents([pdf])


@pytest.mark.asyncio
async def test_empty_answer_is_rejected(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    backend = FakeBackend(SimpleNamespace(answer="", raw_answer="", contexts=[]))
    client = make_client(backend)
    index = await client.index_documents([pdf])
    with pytest.raises(PaperQA2ResponseError, match="empty answer"):
        await client.ask(index, "Question")


@pytest.mark.asyncio
async def test_changed_source_container_is_rejected(tmp_path: Path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    backend = FakeBackend(
        SimpleNamespace(
            answer="Stable answer", raw_answer="", contexts={"changed": True}
        )
    )
    client = make_client(backend)
    index = await client.index_documents([pdf])
    with pytest.raises(PaperQA2ResponseError, match="source data"):
        await client.ask(index, "Question")


def test_factory_rejects_missing_model_and_non_local_url():
    with pytest.raises(PaperQA2ConfigurationError, match="OLLAMA_MODEL"):
        create_paperqa2_client(Settings(OLLAMA_MODEL=""), provider="ollama")
    with pytest.raises(PaperQA2ConfigurationError, match="local HTTP|loopback"):
        create_paperqa2_client(
            Settings(OLLAMA_MODEL="qwen3:4b", OLLAMA_BASE_URL="https://example.com"),
            provider="ollama",
        )


def test_fixed_version_missing_and_mismatch_are_explicit(monkeypatch):
    config = make_client(FakeBackend()).config
    backend = _OfficialPaperQA2Backend(config)

    def missing(_):
        from importlib.metadata import PackageNotFoundError

        raise PackageNotFoundError("paper-qa")

    monkeypatch.setattr(
        "app.integrations.paperqa2.factory.importlib.metadata.version", missing
    )
    from app.integrations.paperqa2.exceptions import (
        PaperQA2NotInstalledError,
        PaperQA2VersionError,
    )

    with pytest.raises(PaperQA2NotInstalledError):
        backend._check_installed_version()

    monkeypatch.setattr(
        "app.integrations.paperqa2.factory.importlib.metadata.version",
        lambda _: "unexpected",
    )
    with pytest.raises(PaperQA2VersionError, match="2026.3.18"):
        backend._check_installed_version()


def test_private_backend_rejects_missing_and_corrupt_indexes(monkeypatch):
    config = make_client(FakeBackend()).config
    backend = _OfficialPaperQA2Backend(config)
    monkeypatch.setattr(backend, "_check_installed_version", lambda: None)
    from app.integrations.paperqa2.exceptions import PaperQA2IndexNotFoundError

    with pytest.raises(PaperQA2IndexNotFoundError):
        backend.ask("missing", "Question")

    backend._indexes["damaged"] = object()
    with pytest.raises(PaperQA2IndexCorruptError):
        backend.ask("damaged", "Question")
