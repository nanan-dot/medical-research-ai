"""A2 API acceptance with explicitly synthetic A0/A1 database fixtures."""

import asyncio
import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_layout.model import (
    DocumentLayoutBlock,
    DocumentLayoutFragment,
    DocumentLayoutSegment,
    DocumentSegmentationRevision,
)
from tests.modules.document_annotation.test_document_annotation_api import client

__all__ = ["client"]


@pytest.fixture
def selection_client(client):
    test_client, document_id, factory = client

    async def prepare():
        async with factory() as session:
            revision = DocumentAnchorRevision(
                document_id=document_id,
                file_hash="a" * 64,
                request_fingerprint="s" * 64,
                extraction_fingerprint="e" * 64,
                extractor_version="x",
                pdfjs_version="6.2.108",
                normalization_version="textitem-norm-2",
                options_hash="o" * 64,
                state="ready",
                created_at=datetime.now(UTC),
            )
            session.add(revision)
            await session.flush()
            layout = DocumentSegmentationRevision(
                anchor_revision_id=revision.id,
                request_fingerprint="l" * 64,
                algorithm_version="test",
                config_hash="c" * 64,
                state="ready",
            )
            session.add(layout)
            await session.flush()
            for number in [1, 2]:
                page = DocumentSourcePage(
                    revision_id=revision.id,
                    page_number=number,
                    width=1000,
                    height=1000,
                    rotation=0,
                    view_box_json="[]",
                    raw_text="Dose 5 mg",
                    normalized_text="Dose 5 mg",
                    text_hash="p" * 64,
                    text_item_count=1,
                )
                session.add(page)
                await session.flush()
                session.add(
                    DocumentSourceTextItem(
                        page_id=page.id,
                        item_index=0,
                        source_array_index=0,
                        raw_text="Dose 5 mg",
                        normalized_text="Dose 5 mg",
                        transform_json="[]",
                        width=100,
                        height=20,
                        has_eol=True,
                        direction="ltr",
                        font_name="Arial",
                        normalized_char_start=0,
                        normalized_char_end=9,
                        raw_utf16_length=9,
                        bbox_json="[80,780,100,20]",
                    )
                )
                session.add(
                    DocumentLayoutBlock(
                        segmentation_revision_id=layout.id,
                        page_id=page.id,
                        block_order=0,
                        block_type="paragraph",
                        text="Dose 5 mg",
                        item_indexes_json="[0]",
                        bbox_json="[0.08,0.2,0.1,0.02]",
                    )
                )
                segment = DocumentLayoutSegment(
                    segmentation_revision_id=layout.id,
                    segment_key=str(number) * 64,
                    reading_order=number - 1,
                    segment_type="paragraph",
                    text="Dose 5 mg",
                    section_path_json="[]",
                    translation_eligibility="eligible",
                    first_page=number,
                    last_page=number,
                )
                session.add(segment)
                await session.flush()
                session.add(
                    DocumentLayoutFragment(
                        segment_id=segment.id,
                        fragment_order=0,
                        page_id=page.id,
                        start_item_index=0,
                        end_item_index=0,
                    )
                )
            await session.commit()
            return revision.id, layout.id

    revision_id, layout_id = asyncio.run(prepare())
    descriptor = {
        "expected_file_hash": "a" * 64,
        "expected_anchor_revision_id": revision_id,
        "expected_segmentation_revision_id": layout_id,
        "browser_quote": "Dose 5 mg",
        "fragments": [
            {
                "page_number": 1,
                "start_item_index": 0,
                "start_offset_utf16": 0,
                "end_item_index": 0,
                "end_offset_utf16": 9,
                "rectangles": [
                    {"left": 0.08, "top": 0.2, "width": 0.1, "height": 0.02}
                ],
            }
        ],
    }
    return test_client, document_id, factory, descriptor


def test_create_reload_and_reuse_exact_anchor(selection_client):
    api, document_id, _, descriptor = selection_client
    first = api.post(f"/api/v1/documents/{document_id}/source-anchors", json=descriptor)
    assert first.status_code == 201, first.text
    second = api.post(
        f"/api/v1/documents/{document_id}/source-anchors", json=descriptor
    )
    assert second.json()["id"] == first.json()["id"]
    reloaded = api.get(f"/api/v1/source-anchors/{first.json()['id']}")
    assert reloaded.json()["resolution_status"] == "exact"
    assert reloaded.json()["quote"] == "Dose 5 mg"
    assert reloaded.json()["fragments"] == descriptor["fragments"]
    assert "prefix" not in reloaded.json()


@pytest.mark.parametrize(
    "change,code",
    [
        ({"browser_quote": "Dose 50 mg"}, "QUOTE_MISMATCH"),
        ({"expected_file_hash": "b" * 64}, "DOCUMENT_REVISION_CONFLICT"),
        ({"expected_anchor_revision_id": 999}, "ANCHOR_REVISION_CONFLICT"),
        ({"expected_segmentation_revision_id": 999}, "SEGMENTATION_REVISION_CONFLICT"),
    ],
)
def test_invalid_selection_is_atomic(selection_client, change, code):
    api, document_id, factory, descriptor = selection_client
    response = api.post(
        f"/api/v1/documents/{document_id}/source-anchors", json={**descriptor, **change}
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == code

    async def count():
        async with factory() as session:
            return await session.scalar(
                select(func.count()).select_from(DocumentSourceAnchor)
            )

    assert asyncio.run(count()) == 0


def test_annotation_and_note_share_anchor_with_idempotency(selection_client):
    api, document_id, _, descriptor = selection_client
    payload = {
        "anchor_descriptor": descriptor,
        "color": "yellow",
        "note": "synthetic test",
    }
    url = f"/api/v1/documents/{document_id}/annotations"
    first = api.post(url, json=payload, headers={"Idempotency-Key": "a2-save"})
    assert first.status_code == 201, first.text
    repeated = api.post(url, json=payload, headers={"Idempotency-Key": "a2-save"})
    assert repeated.json()["id"] == first.json()["id"]
    conflict = api.post(
        url, json={**payload, "note": "changed"}, headers={"Idempotency-Key": "a2-save"}
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"
    anchor_id = first.json()["source_anchor_id"]
    note = api.post(
        f"/api/v1/documents/{document_id}/reading-notes",
        json={"source_anchor_id": anchor_id, "content": "My note"},
        headers={"Idempotency-Key": "a2-note"},
    )
    assert note.status_code == 201, note.text
    assert note.json()["source_anchor_id"] == anchor_id


def test_cross_page_ranges_and_repeat_quote_identity(selection_client):
    api, document_id, _, descriptor = selection_client
    other = json.loads(json.dumps(descriptor))
    other["fragments"][0]["page_number"] = 2
    first = api.post(f"/api/v1/documents/{document_id}/source-anchors", json=descriptor)
    second = api.post(f"/api/v1/documents/{document_id}/source-anchors", json=other)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    multi = {
        **descriptor,
        "browser_quote": "Dose 5 mg Dose 5 mg",
        "fragments": other["fragments"] + descriptor["fragments"],
    }
    response = api.post(f"/api/v1/documents/{document_id}/source-anchors", json=multi)
    assert response.status_code == 201, response.text
    assert [part["page_number"] for part in response.json()["fragments"]] == [1, 2]


def test_page_mapping_returns_fixed_text_and_reading_rank(selection_client):
    api, document_id, _, descriptor = selection_client
    version = {key: value for key, value in descriptor.items() if key.startswith("expected_")}
    response = api.get(f"/api/v1/documents/{document_id}/selection-pages/1", params=version)
    assert response.status_code == 200, response.text
    assert response.json()["items"][0] == {"item_index": 0, "source_array_index": 0,
        "text": "Dose 5 mg", "rank": 0, "eligibility": "eligible"}


def test_position_only_whitespace_does_not_break_anchor_coverage(selection_client):
    api, document_id, factory, descriptor = selection_client

    async def add_position_only_item():
        async with factory() as session:
            page = await session.scalar(
                select(DocumentSourcePage).where(
                    DocumentSourcePage.revision_id
                    == descriptor["expected_anchor_revision_id"],
                    DocumentSourcePage.page_number == 1,
                )
            )
            assert page is not None
            block = await session.scalar(
                select(DocumentLayoutBlock).where(
                    DocumentLayoutBlock.page_id == page.id
                )
            )
            fragment = await session.scalar(
                select(DocumentLayoutFragment).where(
                    DocumentLayoutFragment.page_id == page.id
                )
            )
            assert block is not None and fragment is not None
            session.add(
                DocumentSourceTextItem(
                    page_id=page.id,
                    item_index=1,
                    source_array_index=1,
                    raw_text=" ",
                    normalized_text=" ",
                    transform_json="[]",
                    width=1,
                    height=1,
                    has_eol=False,
                    direction="ltr",
                    font_name="Arial",
                    normalized_char_start=9,
                    normalized_char_end=10,
                    raw_utf16_length=1,
                    bbox_json="[0,0,1,1]",
                )
            )
            block.item_indexes_json = "[0,1]"
            fragment.end_item_index = 1
            await session.commit()

    asyncio.run(add_position_only_item())
    created = api.post(
        f"/api/v1/documents/{document_id}/source-anchors", json=descriptor
    )
    assert created.status_code == 201, created.text
    assert created.json()["quote"] == "Dose 5 mg"


def test_failed_asset_write_rolls_back_new_anchor(selection_client, monkeypatch):
    from app.modules.document_selection.errors import SelectionError
    from app.modules.document_selection.service import SourceAnchorService
    api, document_id, factory, descriptor = selection_client

    async def fail_coverage(*args, **kwargs):
        raise SelectionError("TEXT_MAPPING_INCOMPLETE")

    monkeypatch.setattr(SourceAnchorService, "_coverage", fail_coverage)
    response = api.post(f"/api/v1/documents/{document_id}/annotations",
        json={"anchor_descriptor": descriptor}, headers={"Idempotency-Key": "failed-asset"})
    assert response.status_code == 409

    async def count():
        async with factory() as session:
            return await session.scalar(select(func.count()).select_from(DocumentSourceAnchor))
    assert asyncio.run(count()) == 0


def test_source_authorization_and_old_file_resolution(selection_client):
    from app.modules.document.model import Document
    from app.modules.knowledge_source.model import KnowledgeSource
    api, document_id, factory, descriptor = selection_client
    created = api.post(f"/api/v1/documents/{document_id}/source-anchors", json=descriptor).json()

    async def mutate(disable=False):
        async with factory() as session:
            document = await session.get(Document, document_id)
            document.file_hash = "b" * 64
            if disable:
                source = await session.get(KnowledgeSource, document.knowledge_source_id)
                source.enabled = False
            await session.commit()

    asyncio.run(mutate())
    stale = api.get(f"/api/v1/source-anchors/{created['id']}")
    assert stale.json()["resolution_status"] == "unresolved"
    assert stale.json()["quote"] == "Dose 5 mg"
    asyncio.run(mutate(True))
    denied = api.get(f"/api/v1/source-anchors/{created['id']}")
    assert denied.status_code == 403


def test_concurrent_create_reuses_one_source_anchor(selection_client):
    from app.modules.document_selection.schema import SourceAnchorDescriptor
    from app.modules.document_selection.service import SourceAnchorService
    _, document_id, factory, descriptor = selection_client

    async def create():
        async with factory() as session:
            result = await SourceAnchorService(session).create(document_id, SourceAnchorDescriptor.model_validate(descriptor))
            await session.commit()
            return result.id

    async def run():
        return await asyncio.gather(create(), create())

    ids = asyncio.run(run())
    assert ids[0] == ids[1]
