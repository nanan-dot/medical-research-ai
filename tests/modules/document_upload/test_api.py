import asyncio
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base, get_session
from app.main import app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "uploads.db"
    upload_root = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", upload_root)
    engine = create_async_engine(f"sqlite+aiosqlite:///{database_path.as_posix()}")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def prepare() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def override_session():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    asyncio.run(prepare())
    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client, upload_root
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())


def _make_pdf() -> BytesIO:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    content = BytesIO()
    writer.write(content)
    content.seek(0)
    return content


def test_upload_pdf_creates_managed_document_and_asset(client):
    test_client, upload_root = client

    response = test_client.post(
        "/api/v1/document-uploads",
        files={"file": ("研究论文.PDF", _make_pdf(), "application/pdf")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["document"]["original_filename"] == "研究论文.PDF"
    assert payload["document"]["parse_status"] == "pending"
    assert payload["asset"]["media_type"] == "application/pdf"
    assert payload["asset"]["processing_status"] == "pending_parse"
    assert payload["parse_trigger_url"] == f"/api/v1/documents/{payload['document']['id']}/parse"

    stored_file = upload_root / payload["asset"]["stored_relative_path"]
    assert stored_file.is_file()
    assert stored_file.read_bytes().startswith(b"%PDF-")
    assert not list((upload_root / ".tmp").iterdir())

    detail = test_client.get(f"/api/v1/documents/{payload['document']['id']}")
    assert detail.status_code == 200
    assert detail.json()["original_filename"] == "研究论文.PDF"


@pytest.mark.parametrize(
    ("filename", "content_type", "content"),
    [
        ("paper.txt", "application/pdf", b"%PDF-1.7"),
        ("paper.pdf", "text/plain", b"%PDF-1.7"),
        ("paper.pdf", "application/pdf", b"not a pdf"),
    ],
)
def test_upload_rejects_invalid_file_metadata_or_content(
    client,
    filename: str,
    content_type: str,
    content: bytes,
):
    test_client, upload_root = client

    response = test_client.post(
        "/api/v1/document-uploads",
        files={"file": (filename, BytesIO(content), content_type)},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_pdf_upload"
    assert not (upload_root / "documents").exists() or not list(
        (upload_root / "documents").iterdir()
    )


def test_upload_rejects_more_than_one_file(client):
    test_client, _ = client

    response = test_client.post(
        "/api/v1/document-uploads",
        files=[
            ("file", ("first.pdf", _make_pdf(), "application/pdf")),
            ("file", ("second.pdf", _make_pdf(), "application/pdf")),
        ],
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_pdf_upload"


def test_upload_enforces_configured_size_limit(client, monkeypatch: pytest.MonkeyPatch):
    test_client, _ = client
    monkeypatch.setattr(settings, "MAX_UPLOAD_PDF_BYTES", 64)

    response = test_client.post(
        "/api/v1/document-uploads",
        files={"file": ("large.pdf", _make_pdf(), "application/pdf")},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "pdf_upload_too_large"
