"""A3 legacy annotation backfill acceptance."""

import asyncio
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.modules.conversation.model import Citation, Conversation, Message
from app.modules.document_anchor.model import (
    DocumentSourceAnchor,
    DocumentSourceTextItem,
)
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_relocation.model import (
    AssetAnchorLink,
    LegacyAnchorBackfillItem,
    LegacyAnchorBackfillRun,
)
from app.modules.task.model import TaskRecord


def _legacy_annotation(api, document_id: int) -> dict:
    response = api.post(
        f"/api/v1/documents/{document_id}/annotations",
        json={
            "expected_file_hash": "a" * 64,
            "page_number": 1,
            "rectangles": [{"left": 0.08, "top": 0.2, "width": 0.1, "height": 0.02}],
            "selected_text": "Dose 5 mg",
            "color": "yellow",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _run(api, revision_id: int, mode: str, asset_type: str = "document_annotation"):
    return api.post(
        "/api/v1/document-anchors/backfill-runs",
        headers={"X-Admin-Operation": "confirm"} if mode == "apply" else {},
        json={
            "asset_type": asset_type,
            "source_schema_version": "legacy-annotation-1",
            "target_anchor_revision_id": revision_id,
            "mode": mode,
        },
    )


def test_dry_run_reports_exact_without_writing_anchor_or_link(selection_client) -> None:
    api, document_id, factory, descriptor = selection_client
    legacy = _legacy_annotation(api, document_id)

    async def counts():
        async with factory() as session:
            return (
                await session.scalar(
                    select(func.count()).select_from(DocumentSourceAnchor)
                ),
                await session.scalar(select(func.count()).select_from(AssetAnchorLink)),
            )

    before = asyncio.run(counts())
    response = _run(api, descriptor["expected_anchor_revision_id"], "dry_run")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["exact"] == 1 and body["failed"] == 0
    assert "Dose 5 mg" not in body["report_json"]
    assert asyncio.run(counts()) == before
    assert legacy["source_anchor_id"] is None


def test_apply_backfills_unique_geometry_match_idempotently(selection_client) -> None:
    api, document_id, factory, descriptor = selection_client
    legacy = _legacy_annotation(api, document_id)
    first = _run(api, descriptor["expected_anchor_revision_id"], "apply")
    assert first.status_code == 201, first.text
    assert first.json()["exact"] == 1
    second = _run(api, descriptor["expected_anchor_revision_id"], "apply")
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    async def verify():
        async with factory() as session:
            annotation = await session.get(DocumentAnnotation, legacy["id"])
            links = list((await session.scalars(select(AssetAnchorLink))).all())
            items = list(
                (await session.scalars(select(LegacyAnchorBackfillItem))).all()
            )
            return annotation, links, items

    annotation, links, items = asyncio.run(verify())
    assert annotation.source_anchor_id is not None
    assert len(links) == len(items) == 1
    assert links[0].original_anchor_id == annotation.source_anchor_id


def test_apply_requires_explicit_admin_operation(selection_client) -> None:
    api, _, _, descriptor = selection_client
    response = api.post(
        "/api/v1/document-anchors/backfill-runs",
        json={
            "asset_type": "document_annotation",
            "source_schema_version": "legacy-annotation-1",
            "target_anchor_revision_id": descriptor["expected_anchor_revision_id"],
            "mode": "apply",
        },
    )
    assert response.status_code == 403


def test_deleted_annotation_is_skipped_by_normal_backfill(selection_client) -> None:
    api, document_id, _, descriptor = selection_client
    legacy = _legacy_annotation(api, document_id)
    deleted = api.delete(
        f"/api/v1/documents/{document_id}/annotations/{legacy['id']}?expected_file_hash={'a' * 64}"
    )
    assert deleted.status_code == 204
    result = _run(api, descriptor["expected_anchor_revision_id"], "dry_run").json()
    assert result["total"] == 0


def test_unversioned_citation_never_becomes_exact_even_with_unique_current_match(
    selection_client,
) -> None:
    api, document_id, factory, descriptor = selection_client

    async def seed():
        async with factory() as session:
            now = datetime.now(UTC)
            conversation = Conversation(
                document_ids=str(document_id),
                title="legacy",
                created_at=now,
                updated_at=now,
            )
            session.add(conversation)
            await session.flush()
            message = Message(
                conversation_id=conversation.id,
                sequence=1,
                role="assistant",
                content="historical",
                created_at=now,
            )
            session.add(message)
            await session.flush()
            citation = Citation(
                message_id=message.id,
                document_id=document_id,
                page=1,
                evidence_text="Dose 5 mg",
                citation_text="legacy source",
            )
            session.add(citation)
            await session.commit()
            return citation.id

    citation_id = asyncio.run(seed())
    response = _run(
        api, descriptor["expected_anchor_revision_id"], "dry_run", "citation"
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["candidate"] == 1 and body["exact"] == 0
    assert "Dose 5 mg" not in body["report_json"]

    async def status():
        async with factory() as session:
            return (await session.get(Citation, citation_id)).anchor_status

    assert asyncio.run(status()) == "legacy_unversioned"


def test_repeated_text_with_same_geometry_stays_ambiguous(selection_client) -> None:
    api, document_id, factory, descriptor = selection_client
    _legacy_annotation(api, document_id)

    async def repeat_text():
        async with factory() as session:
            item = await session.get(DocumentSourceTextItem, 1)
            item.raw_text = item.normalized_text = "Dose 5 mg Dose 5 mg"
            item.raw_utf16_length = 19
            await session.commit()

    asyncio.run(repeat_text())
    body = _run(api, descriptor["expected_anchor_revision_id"], "dry_run").json()
    assert body["candidate"] == 1 and body["exact"] == 0


def test_missing_matching_file_revision_stays_unresolved(selection_client) -> None:
    api, document_id, factory, descriptor = selection_client
    legacy = _legacy_annotation(api, document_id)

    async def detach_version():
        async with factory() as session:
            annotation = await session.get(DocumentAnnotation, legacy["id"])
            annotation.file_hash = "b" * 64
            await session.commit()

    asyncio.run(detach_version())
    body = _run(api, descriptor["expected_anchor_revision_id"], "dry_run").json()
    assert body["unresolved"] == 1 and body["exact"] == 0


def test_bad_item_is_recorded_and_next_item_continues(selection_client) -> None:
    api, document_id, factory, descriptor = selection_client
    broken = _legacy_annotation(api, document_id)
    _legacy_annotation(api, document_id)

    async def corrupt_geometry():
        async with factory() as session:
            annotation = await session.get(DocumentAnnotation, broken["id"])
            annotation.selection_geometry = "not-json"
            await session.commit()

    asyncio.run(corrupt_geometry())
    body = _run(api, descriptor["expected_anchor_revision_id"], "dry_run").json()
    assert body["failed"] == 1 and body["exact"] == 1


def test_running_backfill_resumes_from_persisted_primary_key_cursor(
    selection_client,
) -> None:
    api, document_id, factory, descriptor = selection_client
    first = _legacy_annotation(api, document_id)
    _legacy_annotation(api, document_id)

    async def seed_interrupted_run():
        async with factory() as session:
            run = LegacyAnchorBackfillRun(
                asset_type="document_annotation",
                source_schema_version="legacy-annotation-1",
                target_anchor_revision_id=descriptor["expected_anchor_revision_id"],
                mode="dry_run",
                cursor=str(first["id"]),
                total=2,
                scanned=1,
                exact=1,
                algorithm_version="a3-backfill-1",
                status="running",
            )
            session.add(run)
            await session.flush()
            task = TaskRecord(
                task_type="legacy_anchor_backfill",
                title="resume",
                status="running",
                source_type="legacy_anchor_backfill_run",
                source_id=run.id,
                detail_json="{}",
            )
            session.add(task)
            await session.flush()
            run.task_id = task.id
            session.add(
                LegacyAnchorBackfillItem(
                    run_id=run.id,
                    asset_type="document_annotation",
                    asset_id=first["id"],
                    legacy_identity_hash="i" * 64,
                    result_status="exact",
                    anchor_id=None,
                    candidate_count=1,
                    reason_codes_json="[]",
                )
            )
            await session.commit()
            return run.id

    run_id = asyncio.run(seed_interrupted_run())
    body = _run(api, descriptor["expected_anchor_revision_id"], "dry_run").json()
    assert body["id"] == run_id and body["status"] == "completed"
    assert body["scanned"] == 2 and body["exact"] == 2
