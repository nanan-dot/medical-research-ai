import asyncio
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.database import Base, get_session
from app.main import app
from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource

_FILE_HASH = "a" * 64


@pytest.fixture
def client(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'annotations.db').as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    root = tmp_path / "source"
    root.mkdir()
    pdf_path = root / "paper.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    with pdf_path.open("wb") as stream:
        writer.write(stream)

    async def prepare() -> int:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        async with session_factory() as session:
            source = KnowledgeSource(
                name="annotation source",
                source_type="local_folder",
                root_path=str(root),
                normalized_root_path=str(root).casefold(),
                enabled=True,
                sync_status="idle",
            )
            session.add(source)
            await session.flush()
            stat = pdf_path.stat()
            document = Document(
                knowledge_source_id=source.id,
                file_path=pdf_path.name,
                normalized_file_path=pdf_path.name,
                file_hash=_FILE_HASH,
                file_size=stat.st_size,
                modified_time=datetime.fromtimestamp(stat.st_mtime, UTC),
                modified_time_ns=stat.st_mtime_ns,
                scan_state="pending",
                parse_status="succeeded",
                index_status="outdated",
            )
            session.add(document)
            await session.commit()
            return document.id

    async def override_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    document_id = asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client, document_id, session_factory
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _annotation_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "expected_file_hash": _FILE_HASH,
        "page_number": 1,
        "rectangles": [{"left": 0.1, "top": 0.2, "width": 0.3, "height": 0.05}],
        "selected_text": "研究对象",
        "color": "yellow",
        "note": "需要复核",
    }
    payload.update(overrides)
    return payload


def test_create_update_list_and_soft_delete_annotation(client):
    test_client, document_id, _ = client

    created = test_client.post(
        f"/api/v1/documents/{document_id}/annotations",
        json=_annotation_payload(),
    )
    assert created.status_code == 201
    annotation = created.json()
    assert annotation["file_hash"] == _FILE_HASH
    assert annotation["selected_text_hash"]
    assert annotation["version_status"] == "current"

    updated = test_client.patch(
        f"/api/v1/documents/{document_id}/annotations/{annotation['id']}",
        json={"expected_file_hash": _FILE_HASH, "color": "blue", "note": "已复核"},
    )
    assert updated.status_code == 200
    assert updated.json()["color"] == "blue"
    assert updated.json()["note"] == "已复核"

    listed = test_client.get(f"/api/v1/documents/{document_id}/annotations")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [annotation["id"]]

    deleted = test_client.delete(
        f"/api/v1/documents/{document_id}/annotations/{annotation['id']}",
        params={"expected_file_hash": _FILE_HASH},
    )
    assert deleted.status_code == 204
    assert test_client.get(f"/api/v1/documents/{document_id}/annotations").json() == []


def test_rejects_out_of_bounds_geometry_and_stale_document_version(client):
    test_client, document_id, session_factory = client

    invalid_geometry = test_client.post(
        f"/api/v1/documents/{document_id}/annotations",
        json=_annotation_payload(rectangles=[{"left": 0.9, "top": 0, "width": 0.2, "height": 0.1}]),
    )
    assert invalid_geometry.status_code == 422

    created = test_client.post(
        f"/api/v1/documents/{document_id}/annotations",
        json=_annotation_payload(selected_text="<img src=x onerror=alert(1)>"),
    )
    assert created.status_code == 201
    annotation_id = created.json()["id"]

    async def change_document_hash() -> None:
        async with session_factory() as session:
            document = await session.get(Document, document_id)
            assert document is not None
            document.file_hash = "b" * 64
            await session.commit()

    asyncio.run(change_document_hash())
    stale = test_client.get(f"/api/v1/documents/{document_id}/annotations")
    assert stale.status_code == 200
    assert stale.json()[0]["version_status"] == "relocation_required"
    assert stale.json()[0]["selected_text"] == "<img src=x onerror=alert(1)>"

    update = test_client.patch(
        f"/api/v1/documents/{document_id}/annotations/{annotation_id}",
        json={"expected_file_hash": "b" * 64, "note": "should not persist"},
    )
    assert update.status_code == 409
    assert update.json()["error"]["code"] == "annotation_version_conflict"
