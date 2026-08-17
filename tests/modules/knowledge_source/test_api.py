from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    database_path = tmp_path / "api.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    import asyncio

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def create_source(client: TestClient, root: Path, source_type: str = "local_folder"):
    return client.post(
        "/api/v1/knowledge-sources",
        json={"name": root.name, "source_type": source_type, "root_path": str(root)},
    )


def make_pdf() -> BytesIO:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    content = BytesIO()
    writer.write(content)
    content.seek(0)
    return content


def test_browse_directory_returns_selected_path(client: TestClient, monkeypatch):
    selected_path = r"H:\research\papers"
    monkeypatch.setattr(
        "app.modules.knowledge_source.router.select_authorized_directory",
        lambda: selected_path,
    )

    response = client.post("/api/v1/knowledge-sources/browse-directory")

    assert response.status_code == 200
    assert response.json() == {"path": selected_path}


def test_browse_directory_returns_null_when_selection_is_cancelled(
    client: TestClient, monkeypatch
):
    monkeypatch.setattr(
        "app.modules.knowledge_source.router.select_authorized_directory",
        lambda: None,
    )

    response = client.post("/api/v1/knowledge-sources/browse-directory")

    assert response.status_code == 200
    assert response.json() == {"path": None}


def test_browse_directory_returns_clear_4xx_when_picker_is_unavailable(
    client: TestClient, monkeypatch
):
    from app.modules.knowledge_source.browse_service import (
        DIRECTORY_PICKER_UNAVAILABLE_MESSAGE,
        DirectoryPickerUnavailableError,
    )

    def raise_picker_unavailable() -> None:
        raise DirectoryPickerUnavailableError(DIRECTORY_PICKER_UNAVAILABLE_MESSAGE)

    monkeypatch.setattr(
        "app.modules.knowledge_source.router.select_authorized_directory",
        raise_picker_unavailable,
    )

    response = client.post("/api/v1/knowledge-sources/browse-directory")

    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "code": "directory_picker_unavailable",
            "message": DIRECTORY_PICKER_UNAVAILABLE_MESSAGE,
        }
    }


def test_import_document_requires_and_persists_explicit_source(
    client: TestClient, tmp_path: Path
):
    root = tmp_path / "assigned"
    root.mkdir()
    source_id = create_source(client, root).json()["id"]

    response = client.post(
        "/api/v1/knowledge-sources/import-document",
        data={"knowledge_source_id": str(source_id), "relative_directory": "papers/2026"},
        files={"file": ("paper.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["knowledge_source_id"] == source_id
    documents = client.get(f"/api/v1/documents?knowledge_source_id={source_id}")
    assert documents.status_code == 200
    assert documents.json()["items"][0]["knowledge_source_id"] == source_id
    assert list((root / "papers" / "2026").glob("*.pdf"))


def test_import_document_rejects_missing_or_ambiguous_attribution(client: TestClient):
    missing = client.post(
        "/api/v1/knowledge-sources/import-document",
        files={"file": ("paper.pdf", make_pdf(), "application/pdf")},
    )
    both = client.post(
        "/api/v1/knowledge-sources/import-document",
        data={"knowledge_source_id": "1", "new_source_name": "new source"},
        files={"file": ("paper.pdf", make_pdf(), "application/pdf")},
    )
    assert missing.status_code == 400
    assert both.status_code == 400


def test_import_document_creates_visible_source_and_assigns_document(
    client: TestClient, tmp_path: Path
):
    """新建知识库导入：知识库可见（local_folder，非临时导入）、Document 归属正确。"""
    response = client.post(
        "/api/v1/knowledge-sources/import-document",
        data={"new_source_name": "课题 A 补充资料"},
        files={"file": ("paper.pdf", make_pdf(), "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    source_id = payload["knowledge_source_id"]

    # 新建的知识库出现在列表且是普通本地文件夹（用户可见来源，非临时导入）
    sources = client.get("/api/v1/knowledge-sources").json()
    created = next((s for s in sources if s["id"] == source_id), None)
    assert created is not None
    assert created["name"] == "课题 A 补充资料"
    assert created["source_type"] == "local_folder"

    # Document 归属正确
    documents = client.get(f"/api/v1/documents?knowledge_source_id={source_id}")
    assert documents.status_code == 200
    assert documents.json()["items"][0]["knowledge_source_id"] == source_id

    # 没有自动创建"上传文档"等隐式来源
    implicit = [s for s in sources if s["source_type"] == "temporary_import"]
    assert implicit == []


def test_import_document_rejects_duplicate_new_source_name(client: TestClient):
    first = client.post(
        "/api/v1/knowledge-sources/import-document",
        data={"new_source_name": "重复名称"},
        files={"file": ("paper.pdf", make_pdf(), "application/pdf")},
    )
    assert first.status_code == 201

    second = client.post(
        "/api/v1/knowledge-sources/import-document",
        data={"new_source_name": "重复名称"},
        files={"file": ("paper.pdf", make_pdf(), "application/pdf")},
    )
    assert second.status_code == 409


def test_crud_enable_disable_and_delete_preserves_files(
    client: TestClient, tmp_path: Path
):
    root = tmp_path / "papers"
    root.mkdir()
    paper = root / "paper.txt"
    paper.write_text("do not delete", encoding="utf-8")

    created = create_source(client, root)
    assert created.status_code == 201
    source_id = created.json()["id"]

    duplicate = create_source(client, root, "obsidian_vault")
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"

    disabled = client.patch(
        f"/api/v1/knowledge-sources/{source_id}", json={"enabled": False}
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    enabled = client.patch(
        f"/api/v1/knowledge-sources/{source_id}", json={"enabled": True}
    )
    assert enabled.json()["enabled"] is True

    listed = client.get("/api/v1/knowledge-sources")
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [source_id]
    assert listed.json()[0]["stats"] == {
        "total_files": 0,
        "parsed": 0,
        "indexed": 0,
        "pending": 0,
        "failed": 0,
    }
    stats = client.get(f"/api/v1/knowledge-sources/{source_id}/stats")
    assert stats.status_code == 200 and stats.json()["total_files"] == 0

    deleted = client.delete(f"/api/v1/knowledge-sources/{source_id}")
    assert deleted.status_code == 204
    assert paper.read_text(encoding="utf-8") == "do not delete"
    assert client.get(f"/api/v1/knowledge-sources/{source_id}").status_code == 404


def test_stats_for_missing_source_returns_404(client: TestClient):
    response = client.get("/api/v1/knowledge-sources/99999/stats")
    assert response.status_code == 404


def test_missing_path_returns_clear_400(client: TestClient, tmp_path: Path):
    response = create_source(client, tmp_path / "missing", "temporary_import")
    assert response.status_code == 400
    assert response.json()["error"] == {
        "code": "invalid_path",
        "message": "Knowledge source directory does not exist",
    }


def test_permission_and_network_errors_are_explicit(
    client: TestClient, tmp_path: Path, monkeypatch
):
    root = tmp_path / "source"
    root.mkdir()
    monkeypatch.setattr(
        "app.modules.knowledge_source.service.os.access", lambda *_: False
    )
    denied = create_source(client, root)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "permission_denied"

    def unavailable(*_args, **_kwargs):
        raise OSError("network share offline")

    monkeypatch.undo()
    monkeypatch.setattr(Path, "resolve", unavailable)
    response = create_source(client, root)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "temporarily_unavailable"
    assert "network share offline" not in response.text
