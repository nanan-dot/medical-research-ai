import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.modules.document_anchor.extractor_runner import PdfTextItemExtractor
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.publisher import publish
from app.modules.document_layout.model import DocumentSegmentationRevision
from app.modules.document_layout.service import DocumentLayoutService
from app.modules.document_layout.task_lifecycle import (
    cancel_layout_task,
    retry_layout_task,
)
from app.modules.document_layout.worker import DocumentLayoutWorker
from app.modules.task.model import TaskRecord
from app.modules.task.schema import TaskStatus
from tests.modules.document_anchor.support import create_document


@pytest.mark.asyncio
async def test_published_layout_is_queryable_and_preserves_a0_items(
    session, tmp_path
) -> None:
    document, _ = await create_document(session, tmp_path / "paper")
    anchor = DocumentAnchorRevision(
        document_id=document.id,
        file_hash=document.file_hash,
        request_fingerprint="r" * 64,
        extraction_fingerprint="e" * 64,
        extractor_version="x",
        pdfjs_version="x",
        normalization_version="x",
        options_hash="x" * 64,
        state="ready",
        created_at=datetime.now(UTC),
    )
    session.add(anchor)
    await session.flush()
    page = DocumentSourcePage(
        revision_id=anchor.id,
        page_number=1,
        width=1000,
        height=1000,
        rotation=0,
        view_box_json="[]",
        raw_text="Results Dose 5 mg.",
        normalized_text="Results Dose 5 mg.",
        text_hash="t" * 64,
        text_item_count=2,
    )
    session.add(page)
    await session.flush()
    original = "Dose 5 mg."
    session.add_all(
        [
            DocumentSourceTextItem(
                page_id=page.id,
                item_index=0,
                source_array_index=0,
                raw_text="Results",
                normalized_text="Results",
                transform_json="[]",
                width=100,
                height=20,
                has_eol=True,
                direction="ltr",
                font_name="Arial",
                normalized_char_start=0,
                normalized_char_end=7,
                # A0 bbox is PDF space; this puts the heading above the body
                # after A1 converts to its top-left natural reading coordinates.
                bbox_json=json.dumps([400, 880, 500, 900]),
            ),
            DocumentSourceTextItem(
                page_id=page.id,
                item_index=1,
                source_array_index=1,
                raw_text=original,
                normalized_text=original,
                transform_json="[]",
                width=200,
                height=20,
                has_eol=True,
                direction="ltr",
                font_name="Arial",
                normalized_char_start=8,
                normalized_char_end=18,
                bbox_json=json.dumps([80, 780, 280, 800]),
            ),
        ]
    )
    await session.commit()
    service = DocumentLayoutService(session)
    requested = await service.request(anchor.id)
    await service.execute(requested.id)
    await session.commit()
    page_result = await service.segments(document.id, 1, 0, 20)
    assert [item.text for item in page_result.items] == ["Results", "Dose 5 mg."]
    assert page_result.items[1].fragments[0].start_item_index == 1
    sections = await service.sections(document.id)
    assert sections[0].literal_title == "Results"
    section_result = await service.section_segments(document.id, sections[0].id, 0, 20)
    assert [item.text for item in section_result.items] == ["Results", "Dose 5 mg."]
    refreshed = await session.get(DocumentSourceTextItem, 2)
    assert refreshed is not None and refreshed.raw_text == original


@pytest.mark.asyncio
async def test_republish_demotes_previous_current_revision_before_promotion(
    session, tmp_path
) -> None:
    document, _ = await create_document(session, tmp_path / "republish")
    anchor = DocumentAnchorRevision(
        document_id=document.id, file_hash=document.file_hash,
        request_fingerprint="u" * 64, extraction_fingerprint="v" * 64,
        extractor_version="x", pdfjs_version="x", normalization_version="x",
        options_hash="x" * 64, state="ready", created_at=datetime.now(UTC),
    )
    session.add(anchor)
    await session.flush()
    page = DocumentSourcePage(
        revision_id=anchor.id, page_number=1, width=1000, height=1000, rotation=0,
        view_box_json="[]", raw_text="Dose 5 mg.", normalized_text="Dose 5 mg.",
        text_hash="r" * 64, text_item_count=1,
    )
    session.add(page)
    await session.flush()
    session.add(DocumentSourceTextItem(
        page_id=page.id, item_index=0, source_array_index=0, raw_text="Dose 5 mg.",
        normalized_text="Dose 5 mg.", transform_json="[]", width=200, height=20,
        has_eol=True, direction="ltr", font_name="Arial", normalized_char_start=0,
        normalized_char_end=10, bbox_json=json.dumps([80, 780, 280, 800]),
    ))
    old = DocumentSegmentationRevision(
        anchor_revision_id=anchor.id, request_fingerprint="o" * 64,
        algorithm_version="legacy", config_hash="o" * 64, state="ready",
    )
    new = DocumentSegmentationRevision(
        anchor_revision_id=anchor.id, request_fingerprint="n" * 64,
        algorithm_version="current", config_hash="n" * 64, state="pending",
    )
    session.add_all([old, new])
    await session.commit()

    await DocumentLayoutService(session).execute(new.id)
    await session.commit()

    assert (await session.get(DocumentSegmentationRevision, old.id)).state == "stale"
    assert (await session.get(DocumentSegmentationRevision, new.id)).state == "ready"


@pytest.mark.asyncio
async def test_section_segments_do_not_leak_into_next_same_page_section(
    session, tmp_path
) -> None:
    document, _ = await create_document(session, tmp_path / "section-boundary")
    anchor = DocumentAnchorRevision(
        document_id=document.id,
        file_hash=document.file_hash,
        request_fingerprint="b" * 64,
        extraction_fingerprint="a" * 64,
        extractor_version="x",
        pdfjs_version="x",
        normalization_version="x",
        options_hash="x" * 64,
        state="ready",
        created_at=datetime.now(UTC),
    )
    session.add(anchor)
    await session.flush()
    page = DocumentSourcePage(
        revision_id=anchor.id,
        page_number=1,
        width=1000,
        height=1000,
        rotation=0,
        view_box_json="[]",
        raw_text="Results First finding. Discussion Second finding.",
        normalized_text="Results First finding. Discussion Second finding.",
        text_hash="s" * 64,
        text_item_count=4,
    )
    session.add(page)
    await session.flush()
    rows = [
        ("Results", 850),
        ("First finding.", 780),
        ("Discussion", 650),
        ("Second finding.", 580),
    ]
    session.add_all(
        DocumentSourceTextItem(
            page_id=page.id,
            item_index=index,
            source_array_index=index,
            raw_text=value,
            normalized_text=value,
            transform_json="[]",
            width=300,
            height=20,
            has_eol=True,
            direction="ltr",
            font_name="Arial",
            normalized_char_start=index * 10,
            normalized_char_end=index * 10 + len(value),
            bbox_json=json.dumps([80, y, 380, y + 20]),
        )
        for index, (value, y) in enumerate(rows)
    )
    await session.commit()
    service = DocumentLayoutService(session)
    requested = await service.request(anchor.id)
    await service.execute(requested.id)
    await session.commit()

    sections = await service.sections(document.id)
    result = await service.section_segments(document.id, sections[0].id, 0, 20)

    assert sections[0].literal_title == "Results"
    assert [item.text for item in result.items] == ["Results", "First finding."]


@pytest.mark.asyncio
async def test_cancel_and_retry_never_publish_partial_layout(session, tmp_path) -> None:
    document, _ = await create_document(session, tmp_path / "cancel")
    anchor = DocumentAnchorRevision(
        document_id=document.id,
        file_hash=document.file_hash,
        request_fingerprint="c" * 64,
        extraction_fingerprint="f" * 64,
        extractor_version="x",
        pdfjs_version="x",
        normalization_version="x",
        options_hash="x" * 64,
        state="ready",
        created_at=datetime.now(UTC),
    )
    session.add(anchor)
    await session.flush()
    revision = DocumentSegmentationRevision(
        anchor_revision_id=anchor.id,
        request_fingerprint="s" * 64,
        algorithm_version="a",
        config_hash="c" * 64,
        state="pending",
    )
    session.add(revision)
    await session.flush()
    task = TaskRecord(
        task_type="document_layout_segmentation",
        title="layout",
        status="queued",
        idempotency_key="segment-test",
        active_idempotency_key="segment-test",
        detail_json=json.dumps({"segmentation_revision_id": revision.id}),
    )
    session.add(task)
    await session.flush()
    await cancel_layout_task(session, task)
    assert revision.state == "cancelled"
    task.status = "failed"
    task.error_code = "layout_segmentation_failed"
    await session.flush()
    await retry_layout_task(session, task)
    assert task.status == "queued"
    assert revision.state == "pending"


@pytest.mark.asyncio
async def test_a0_scan_quality_blocks_derived_translation_flow(
    session, tmp_path
) -> None:
    document, _ = await create_document(session, tmp_path / "scan")
    anchor = DocumentAnchorRevision(
        document_id=document.id,
        file_hash=document.file_hash,
        request_fingerprint="q" * 64,
        extraction_fingerprint="z" * 64,
        extractor_version="x",
        pdfjs_version="x",
        normalization_version="x",
        options_hash="x" * 64,
        state="ready",
        created_at=datetime.now(UTC),
    )
    session.add(anchor)
    await session.flush()
    page = DocumentSourcePage(
        revision_id=anchor.id,
        page_number=1,
        width=1000,
        height=1000,
        rotation=0,
        view_box_json="[]",
        raw_text="Uncertain",
        normalized_text="Uncertain",
        text_hash="u" * 64,
        text_item_count=1,
        quality_flags_json='["scan_detected"]',
    )
    session.add(page)
    await session.flush()
    session.add(
        DocumentSourceTextItem(
            page_id=page.id,
            item_index=0,
            source_array_index=0,
            raw_text="Uncertain",
            normalized_text="Uncertain",
            transform_json="[]",
            width=100,
            height=20,
            has_eol=True,
            direction="ltr",
            font_name="Arial",
            normalized_char_start=0,
            normalized_char_end=9,
            bbox_json="[80,200,180,220]",
        )
    )
    await session.commit()
    service = DocumentLayoutService(session)
    requested = await service.request(anchor.id)
    await service.execute(requested.id)
    await session.commit()
    assert (await service.segments(document.id, 1, 0, 10)).items[
        0
    ].translation_eligibility == "blocked"


@pytest.mark.asyncio
async def test_worker_claims_and_publishes_one_queued_layout(
    session_factory, tmp_path
) -> None:
    async with session_factory() as session:
        document, _ = await create_document(session, tmp_path / "worker")
        anchor = DocumentAnchorRevision(
            document_id=document.id,
            file_hash=document.file_hash,
            request_fingerprint="w" * 64,
            extraction_fingerprint="v" * 64,
            extractor_version="x",
            pdfjs_version="x",
            normalization_version="x",
            options_hash="x" * 64,
            state="ready",
            created_at=datetime.now(UTC),
        )
        session.add(anchor)
        await session.flush()
        page = DocumentSourcePage(
            revision_id=anchor.id,
            page_number=1,
            width=1000,
            height=1000,
            rotation=0,
            view_box_json="[]",
            raw_text="Body.",
            normalized_text="Body.",
            text_hash="b" * 64,
            text_item_count=1,
        )
        session.add(page)
        await session.flush()
        session.add(
            DocumentSourceTextItem(
                page_id=page.id,
                item_index=0,
                source_array_index=0,
                raw_text="Body.",
                normalized_text="Body.",
                transform_json="[]",
                width=100,
                height=20,
                has_eol=True,
                direction="ltr",
                font_name="Arial",
                normalized_char_start=0,
                normalized_char_end=5,
                bbox_json="[80,200,180,220]",
            )
        )
        requested = await DocumentLayoutService(session).request(anchor.id)
        task_id = requested.task_id
        assert task_id is not None
        await session.commit()
    assert await DocumentLayoutWorker(session_factory).run_once()
    async with session_factory() as session:
        task = await session.get(TaskRecord, task_id)
        revision = await session.get(DocumentSegmentationRevision, requested.id)
        assert task is not None and task.status == "succeeded"
        assert revision is not None and revision.state == "ready"


@pytest.mark.asyncio
async def test_worker_requeues_transient_failure_with_no_publication(
    session_factory, tmp_path, monkeypatch
) -> None:
    async with session_factory() as session:
        document, _ = await create_document(session, tmp_path / "retry")
        anchor = DocumentAnchorRevision(
            document_id=document.id,
            file_hash=document.file_hash,
            request_fingerprint="y" * 64,
            extraction_fingerprint="h" * 64,
            extractor_version="x",
            pdfjs_version="x",
            normalization_version="x",
            options_hash="x" * 64,
            state="ready",
            created_at=datetime.now(UTC),
        )
        session.add(anchor)
        await session.flush()
        revision = DocumentSegmentationRevision(
            anchor_revision_id=anchor.id,
            request_fingerprint="k" * 64,
            algorithm_version="a",
            config_hash="c" * 64,
            state="pending",
        )
        session.add(revision)
        await session.flush()
        task = TaskRecord(
            task_type="document_layout_segmentation",
            title="layout",
            status="queued",
            idempotency_key="retry-layout",
            active_idempotency_key="retry-layout",
            detail_json=json.dumps({"segmentation_revision_id": revision.id}),
        )
        session.add(task)
        await session.commit()

    async def fail(*_args, **_kwargs) -> None:
        raise RuntimeError("temporary")

    monkeypatch.setattr(DocumentLayoutService, "execute", fail)
    assert await DocumentLayoutWorker(session_factory).run_once()
    async with session_factory() as session:
        task = await session.get(TaskRecord, task.id)
        revision = await session.get(DocumentSegmentationRevision, revision.id)
        assert task is not None and task.status == "queued"
        assert revision is not None and revision.state == "pending"


@pytest.mark.asyncio
async def test_concurrent_workers_claim_one_layout_task(
    session_factory, tmp_path
) -> None:
    async with session_factory() as session:
        document, _ = await create_document(session, tmp_path / "concurrent")
        anchor = DocumentAnchorRevision(
            document_id=document.id,
            file_hash=document.file_hash,
            request_fingerprint="n" * 64,
            extraction_fingerprint="p" * 64,
            extractor_version="x",
            pdfjs_version="x",
            normalization_version="x",
            options_hash="x" * 64,
            state="ready",
            created_at=datetime.now(UTC),
        )
        session.add(anchor)
        await session.flush()
        page = DocumentSourcePage(
            revision_id=anchor.id,
            page_number=1,
            width=1000,
            height=1000,
            rotation=0,
            view_box_json="[]",
            raw_text="Body.",
            normalized_text="Body.",
            text_hash="d" * 64,
            text_item_count=1,
        )
        session.add(page)
        await session.flush()
        session.add(
            DocumentSourceTextItem(
                page_id=page.id,
                item_index=0,
                source_array_index=0,
                raw_text="Body.",
                normalized_text="Body.",
                transform_json="[]",
                width=100,
                height=20,
                has_eol=True,
                direction="ltr",
                font_name="Arial",
                normalized_char_start=0,
                normalized_char_end=5,
                bbox_json="[80,200,180,220]",
            )
        )
        await DocumentLayoutService(session).request(anchor.id)
        await session.commit()
    outcomes = await asyncio.gather(
        DocumentLayoutWorker(session_factory).run_once(),
        DocumentLayoutWorker(session_factory).run_once(),
    )
    async with session_factory() as session:
        tasks = list((await session.scalars(select(TaskRecord))).all())
        revisions = list(
            (await session.scalars(select(DocumentSegmentationRevision))).all()
        )
    assert outcomes.count(True) == 1
    assert len(tasks) == len(revisions) == 1
    assert tasks[0].status == TaskStatus.SUCCEEDED.value
    assert tasks[0].active_idempotency_key is None
    assert revisions[0].state == "ready"


@pytest.mark.asyncio
async def test_real_a0_pdfjs_output_can_publish_a1_segments(session, tmp_path) -> None:
    source_pdf = Path("data/anchor_validation/complex.pdf").resolve()
    assert source_pdf.is_file()
    document, _ = await create_document(session, tmp_path / "real-a1")
    source_hash = hashlib.sha256(source_pdf.read_bytes()).hexdigest()
    document.file_hash = source_hash
    revision = DocumentAnchorRevision(
        document_id=document.id,
        file_hash=source_hash,
        request_fingerprint="g" * 64,
        extractor_version="x",
        pdfjs_version="x",
        normalization_version="x",
        options_hash="x" * 64,
        state="pending",
        created_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.flush()
    stream = await PdfTextItemExtractor().extract(source_pdf, source_hash, "a1-real-db")
    try:
        await publish(session, revision, stream)
    finally:
        stream.close()
    await session.commit()
    requested = await DocumentLayoutService(session).request(revision.id)
    await DocumentLayoutService(session).execute(requested.id)
    await session.commit()
    result = await DocumentLayoutService(session).segments(document.id, None, 0, 200)
    assert result.total >= 1
    assert all(
        item.translation_eligibility in {"eligible", "review_required", "blocked"}
        for item in result.items
    )
