import asyncio
from pathlib import Path

import pytest

from app.common.exceptions import ConflictError
from app.common.hashing import sha256_file
from app.integrations.paperqa2 import PaperQAIndex
from app.integrations.paperqa2.exceptions import PaperQA2OperationError
from app.modules.document.index_service import DocumentIndexService
from app.modules.document.schema import IndexStatus
from tests.modules.document.conftest import create_document


class FakePaperQAClient:
    def __init__(self, *, fail_name: str | None = None) -> None:
        self.calls: list[tuple[Path, bool]] = []
        self.fail_name = fail_name

    async def index_documents(self, documents, *, rebuild=False):
        document = documents[0]
        self.calls.append((document.path, rebuild))
        if document.path.name == self.fail_name:
            raise PaperQA2OperationError("indexing unavailable")
        return PaperQAIndex(index_id=f"idx-{document.path.stem}", document_count=1, reused=False)


async def prepared_document(session, tmp_path: Path, name: str = "paper.txt"):
    document, path = await create_document(
        session, tmp_path / name.replace(".", "-"), name, parse_status="succeeded"
    )
    document.file_hash = sha256_file(path)
    await session.commit()
    return document, path


@pytest.mark.asyncio
async def test_single_index_persists_mapping_and_reuses_it(session, tmp_path: Path):
    document, path = await prepared_document(session, tmp_path)
    client = FakePaperQAClient()
    service = DocumentIndexService(
        session, client_factory=lambda: client, index_root=tmp_path / "indexes", paperqa_version="1.0"
    )

    first = await service.index(document.id)
    second = await service.index(document.id)

    assert first.index_status == IndexStatus.SUCCEEDED
    assert first.paperqa_index_key == "idx-paper"
    assert second.reused is True
    assert len(client.calls) == 1
    assert path.read_text(encoding="utf-8") == "test fixture"
    assert (tmp_path / "indexes" / f"document-{document.id}" / "metadata.json").is_file()


@pytest.mark.asyncio
async def test_changed_source_is_marked_outdated(session, tmp_path: Path):
    document, path = await prepared_document(session, tmp_path)
    path.write_text("changed", encoding="utf-8")

    with pytest.raises(ConflictError, match="synchronized"):
        await DocumentIndexService(
            session, client_factory=FakePaperQAClient, index_root=tmp_path / "indexes"
        ).index(document.id)

    assert document.index_status == IndexStatus.OUTDATED.value


@pytest.mark.asyncio
async def test_version_change_rebuilds_index(session, tmp_path: Path):
    document, _ = await prepared_document(session, tmp_path)
    client = FakePaperQAClient()
    root = tmp_path / "indexes"
    await DocumentIndexService(
        session, client_factory=lambda: client, index_root=root, paperqa_version="1.0"
    ).index(document.id)
    result = await DocumentIndexService(
        session, client_factory=lambda: client, index_root=root, paperqa_version="2.0"
    ).index(document.id)

    assert result.paperqa_version == "2.0"
    assert client.calls[-1][1] is True


@pytest.mark.asyncio
async def test_batch_keeps_partial_success(session, tmp_path: Path):
    good, _ = await prepared_document(session, tmp_path, "good.txt")
    bad, _ = await prepared_document(session, tmp_path, "bad.txt")
    client = FakePaperQAClient(fail_name="bad.txt")

    result = await DocumentIndexService(
        session, client_factory=lambda: client, index_root=tmp_path / "indexes"
    ).batch_index([good.id, bad.id])

    assert result.succeeded == 1
    assert result.failed == 1
    assert result.results[0].index_status == IndexStatus.SUCCEEDED
    assert result.results[1].index_status == IndexStatus.FAILED
    assert bad.index_status == IndexStatus.FAILED.value


@pytest.mark.asyncio
async def test_failed_index_can_be_retried(session, tmp_path: Path):
    document, _ = await prepared_document(session, tmp_path, "retry.txt")
    failing = FakePaperQAClient(fail_name="retry.txt")
    root = tmp_path / "indexes"
    with pytest.raises(ConflictError, match="unavailable"):
        await DocumentIndexService(
            session, client_factory=lambda: failing, index_root=root
        ).index(document.id)

    successful = FakePaperQAClient()
    result = await DocumentIndexService(
        session, client_factory=lambda: successful, index_root=root
    ).index(document.id)

    assert result.index_status == IndexStatus.SUCCEEDED
    assert document.index_error is None


@pytest.mark.asyncio
async def test_delete_clears_mapping_without_touching_source(session, tmp_path: Path):
    document, path = await prepared_document(session, tmp_path)
    service = DocumentIndexService(
        session, client_factory=FakePaperQAClient, index_root=tmp_path / "indexes"
    )
    await service.index(document.id)

    result = await service.delete_index(document.id)

    assert result.index_status == IndexStatus.PENDING
    assert result.paperqa_index_key is None
    assert path.is_file()


@pytest.mark.asyncio
async def test_concurrent_index_for_same_document_is_rejected(session, tmp_path: Path):
    document, _ = await prepared_document(session, tmp_path)
    started = asyncio.Event()
    release = asyncio.Event()

    class SlowClient(FakePaperQAClient):
        async def index_documents(self, documents, *, rebuild=False):
            started.set()
            await release.wait()
            return await super().index_documents(documents, rebuild=rebuild)

    service = DocumentIndexService(
        session, client_factory=SlowClient, index_root=tmp_path / "indexes"
    )
    task = asyncio.create_task(service.index(document.id))
    await started.wait()
    with pytest.raises(ConflictError, match="already running"):
        await service.index(document.id)
    release.set()
    await task


@pytest.mark.asyncio
async def test_namespace_conflict_marks_task_failed(session, tmp_path: Path):
    document, _ = await prepared_document(session, tmp_path)
    namespace = tmp_path / "indexes" / f"document-{document.id}"
    namespace.mkdir(parents=True)
    (namespace / "metadata.json").write_text('{"document_id": 999}', encoding="utf-8")

    with pytest.raises(ConflictError, match="conflicts"):
        await DocumentIndexService(
            session, client_factory=FakePaperQAClient, index_root=tmp_path / "indexes"
        ).index(document.id)

    assert document.index_status == IndexStatus.FAILED.value
    assert document.error_code == "index_namespace_conflict"
