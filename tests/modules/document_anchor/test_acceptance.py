"""A0 behavior-level acceptance coverage derived from the anchor designs."""

import asyncio
import hashlib

import pytest
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import NotFoundError
from app.core import models  # noqa: F401
from app.core.config import settings
from app.core.database import Base
from app.modules.document_anchor.contract import (
    ContractValidationError,
    validate_records,
)
from app.modules.document_anchor.extractor_runner import (
    ExtractorUnavailableError,
    PdfTextItemExtractor,
)
from app.modules.document_anchor.fingerprint import (
    request_fingerprint,
)
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_anchor.normalization import (
    NORMALIZATION_VERSION,
    normalize_text_item,
)
from app.modules.document_anchor.schema import AnchorRevisionRequest
from app.modules.document_anchor.service import OPTIONS_HASH, DocumentAnchorService
from app.modules.document_anchor.toolchain import identity
from app.modules.document_anchor.worker import DocumentAnchorWorker
from app.modules.task.model import TaskRecord
from app.modules.task.schema import TaskStatus
from tests.modules.document_anchor.support import create_document, seal


def _header() -> dict[str, object]:
    return {
        "record_type": "header",
        "contract_schema_version": identity()["contract_schema_version"],
        "request_id": "request-1",
        "extractor_version": identity()["extractor_version"],
        "pdfjs_version": "6.2.108",
        "normalization_version": NORMALIZATION_VERSION,
        "file_sha256": "a" * 64,
        "options_hash": OPTIONS_HASH,
        "page_count": 1,
    }


def _page() -> dict[str, object]:
    return {
        "record_type": "page",
        "page_number": 1,
        "width": 612.0,
        "height": 792.0,
        "rotation": 0,
        "view_box": [0.0, 0.0, 612.0, 792.0],
        "items": [
            {
                "item_index": 0,
                "source_array_index": 0,
                "text": "Dose 5 mg",
                "direction": "ltr",
                "transform": [12.0, 0.0, 0.0, 12.0, 72.0, 700.0],
                "width": 48.2,
                "height": 12.0,
                "font_name": "f1",
                "has_eol": True,
            }
        ],
        "styles": {
            "f1": {
                "font_family": "serif",
                "ascent": 0.9,
                "descent": -0.2,
                "vertical": False,
            }
        },
    }


def _trailer() -> dict[str, object]:
    return {
        "record_type": "trailer",
        "request_id": "request-1",
        "pages_emitted": 1,
        "items_emitted": 1,
        "completed": True,
    }


def test_fingerprint_is_deterministic() -> None:
    first = request_fingerprint(
        "a" * 64, "1.0.0", "6.2.108", NORMALIZATION_VERSION, "b" * 64
    )
    second = request_fingerprint(
        "a" * 64, "1.0.0", "6.2.108", NORMALIZATION_VERSION, "b" * 64
    )
    assert first == second


def test_normalization_preserves_raw_text_and_sensitive_symbols() -> None:
    result = normalize_text_item("interven-\u00ad\n tion 5−10 μg \x00")
    assert result.raw_text == "interven-\u00ad\n tion 5−10 μg \x00"
    assert "5−10 μg" in result.normalized_text
    assert "\x00" not in result.normalized_text
    assert result.normalization_version == NORMALIZATION_VERSION


def test_contract_accepts_complete_coordinate_stream() -> None:
    stream = validate_records(seal(_header(), [_page()], _trailer()))
    assert stream.pages[0].items[0].transform[-2:] == (72.0, 700.0)
    assert stream.pages[0].items[0].font_name == "f1"


@pytest.mark.parametrize(
    "records", [[_header(), _page()], [_header(), _page(), _page(), _trailer()]]
)
def test_contract_rejects_incomplete_or_invalid_stream(
    records: list[dict[str, object]],
) -> None:
    with pytest.raises(ContractValidationError):
        validate_records(records)


def test_empty_page_is_review_required() -> None:
    page = _page()
    page["items"] = []
    trailer = _trailer()
    trailer["items_emitted"] = 0
    stream = validate_records(seal(_header(), [page], trailer))
    assert "NO_SELECTABLE_TEXT" in stream.quality_flags[0]


class _FixedExtractor:
    async def extract(self, _path, _sha256: str, _request_id: str):
        header = _header()
        header["options_hash"] = OPTIONS_HASH
        header["file_sha256"] = _sha256
        header["request_id"] = _request_id
        trailer = _trailer()
        trailer["request_id"] = _request_id
        return validate_records(seal(header, [_page()], trailer))


@pytest.mark.asyncio
async def test_repeated_submission_is_idempotent(session, tmp_path) -> None:
    document, _path = await create_document(
        session, tmp_path / "source", name="paper.pdf"
    )
    request = AnchorRevisionRequest(expected_file_hash=document.file_hash)
    service = DocumentAnchorService(session)

    first = await service.request(document.id, request)
    second = await service.request(document.id, request)

    assert first.id == second.id
    assert first.task_id == second.task_id


@pytest.mark.asyncio
async def test_request_probe_is_coalesced_within_ttl(session, tmp_path, monkeypatch) -> None:
    from app.modules.document_anchor import service as service_module

    document, _ = await create_document(session, tmp_path / "source")
    calls = 0

    async def probe(_self):
        nonlocal calls
        calls += 1
        return {"extractor_version": "test"}

    service_module._probe_cache = None
    monkeypatch.setattr(PdfTextItemExtractor, "probe", probe)
    request = AnchorRevisionRequest(expected_file_hash=document.file_hash)
    await DocumentAnchorService(session).request(document.id, request)
    await DocumentAnchorService(session).request(document.id, request)
    assert calls == 1


@pytest.mark.asyncio
async def test_completed_submission_reuses_ready_revision(session, tmp_path) -> None:
    document, _path = await create_document(
        session, tmp_path / "source", name="paper.pdf"
    )
    request = AnchorRevisionRequest(expected_file_hash=document.file_hash)
    service = DocumentAnchorService(session)
    queued = await service.request(document.id, request)
    await service.execute(queued.id, _FixedExtractor())

    reused = await service.request(document.id, request)

    assert reused.id == queued.id
    assert reused.task_id is None


@pytest.mark.asyncio
async def test_failure_does_not_publish_partial_revision(
    session, tmp_path, monkeypatch
) -> None:
    document, _path = await create_document(
        session, tmp_path / "source", name="broken.pdf"
    )
    revision = await DocumentAnchorService(session).request(
        document.id, AnchorRevisionRequest(expected_file_hash=document.file_hash)
    )

    monkeypatch.setattr(settings, "PDF_TEXTITEM_EXTRACTOR_COMMAND", "")
    with pytest.raises(ExtractorUnavailableError):
        await DocumentAnchorService(session).execute(revision.id)

    manifest = await DocumentAnchorService(session).manifest(document.id)
    stored = await session.get(DocumentAnchorRevision, revision.id)
    assert manifest.revision is None
    assert stored is not None and stored.state == "failed"


@pytest.mark.asyncio
async def test_revision_is_scoped_to_its_document(session, tmp_path) -> None:
    first_document, _first_path = await create_document(
        session, tmp_path / "one", name="one.pdf"
    )
    second_document, _ = await create_document(
        session, tmp_path / "two", name="two.pdf"
    )
    service = DocumentAnchorService(session)
    revision = await service.request(
        first_document.id,
        AnchorRevisionRequest(expected_file_hash=first_document.file_hash),
    )
    await service.execute(revision.id, _FixedExtractor())

    with pytest.raises(NotFoundError):
        await service.page_quality(second_document.id, revision.id, 1)


@pytest.mark.asyncio
async def test_real_pdfjs_extractor_returns_positioned_text_items(
    tmp_path, monkeypatch
) -> None:
    """AC-03: the independent Node/PDF.js path yields a validated real stream."""
    pdf_path = tmp_path / "fixture.pdf"
    document = canvas.Canvas(str(pdf_path))
    document.drawString(72, 720, "Dose 5 mg")
    document.save()
    import hashlib

    file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    monkeypatch.setattr(
        settings,
        "PDF_TEXTITEM_EXTRACTOR_COMMAND",
        "node tools/pdf_textitem_extractor/src/cli.mjs",
    )
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path / "data")

    stream = await PdfTextItemExtractor().extract(pdf_path, file_hash, "real-pdf")

    assert stream.pages[0].items[0].text == "Dose 5 mg"
    assert stream.pages[0].items[0].transform[-2:] != (0.0, 0.0)
    assert not list((tmp_path / "data" / "anchor_extractor").glob("*.json"))


def test_anchor_revision_api_creates_and_reuses_pending_task(api_context) -> None:
    """AC-07: the public API returns one durable pending revision and task."""
    client, document_id, path = api_context
    payload = {"expected_file_hash": hashlib.sha256(path.read_bytes()).hexdigest()}

    first = client.post(
        f"/api/v1/documents/{document_id}/anchor-revisions",
        json=payload,
        headers={"Idempotency-Key": "a0-test-key"},
    )
    second = client.post(
        f"/api/v1/documents/{document_id}/anchor-revisions",
        json=payload,
        headers={"Idempotency-Key": "a0-test-key"},
    )
    manifest = client.get(f"/api/v1/documents/{document_id}/anchor-manifest")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["task_id"] == second.json()["task_id"]
    assert manifest.status_code == 200
    assert manifest.json()["revision"] is None


@pytest.mark.asyncio
async def test_concurrent_workers_claim_one_anchor_task(tmp_path) -> None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'workers.db').as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        document, _ = await create_document(session, tmp_path / "source")
        await DocumentAnchorService(session).request(
            document.id, AnchorRevisionRequest(expected_file_hash=document.file_hash)
        )
        await session.commit()
    outcomes = await asyncio.gather(
        DocumentAnchorWorker(sessions).run_once(),
        DocumentAnchorWorker(sessions).run_once(),
    )
    async with sessions() as session:
        tasks = list((await session.scalars(select(TaskRecord))).all())
        revision = await session.get(DocumentAnchorRevision, 1)
        assert revision.state in {"ready", "review_required"}
    await engine.dispose()
    assert outcomes.count(True) == 1
    assert tasks[0].status == TaskStatus.SUCCEEDED.value
    assert tasks[0].active_idempotency_key is None
