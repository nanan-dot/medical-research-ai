import asyncio

import pytest

from app.modules.medical_translation.model import MedicalTranslationJob
from tests.modules.document_annotation.test_document_annotation_api import client
from tests.modules.document_selection.test_api import selection_client

__all__ = ["client", "selection_client"]


@pytest.fixture
def translation_context(selection_client):
    api, document_id, factory, descriptor = selection_client
    anchor = api.post(
        f"/api/v1/documents/{document_id}/source-anchors", json=descriptor
    ).json()
    return api, document_id, factory, anchor


def test_create_job_is_idempotent_and_exposes_safe_status(translation_context):
    api, document_id, factory, anchor = translation_context
    payload = {
        "source_anchor_id": anchor["id"],
        "source_language": "en",
        "target_language": "zh-CN",
    }
    headers = {"Idempotency-Key": "translate-selection-1"}
    first = api.post(
        f"/api/v1/documents/{document_id}/translation-jobs",
        json=payload,
        headers=headers,
    )
    assert first.status_code == 202, first.text
    repeated = api.post(
        f"/api/v1/documents/{document_id}/translation-jobs",
        json=payload,
        headers=headers,
    )
    assert repeated.status_code == 202
    assert repeated.json()["id"] == first.json()["id"]
    status = api.get(f"/api/v1/translation-jobs/{first.json()['id']}")
    assert status.status_code == 200
    assert status.json()["state"] == "queued"
    assert "source_text" not in status.json()

    async def assert_interactive_priority():
        async with factory() as session:
            job = await session.get(MedicalTranslationJob, first.json()["id"])
            assert job is not None
            assert job.request_priority == 3
            assert job.request_trigger == "selection"

    asyncio.run(assert_interactive_priority())


def test_cross_document_anchor_is_rejected(translation_context):
    api, _, _, anchor = translation_context
    response = api.post(
        "/api/v1/documents/999999/translation-jobs",
        json={
            "source_anchor_id": anchor["id"],
            "source_language": "en",
            "target_language": "zh-CN",
        },
        headers={"Idempotency-Key": "cross-document"},
    )
    assert response.status_code in {403, 404, 409}


def test_cancel_and_retry_have_legal_terminal_behavior(translation_context):
    api, document_id, _, anchor = translation_context
    created = api.post(
        f"/api/v1/documents/{document_id}/translation-jobs",
        json={
            "source_anchor_id": anchor["id"],
            "source_language": "en",
            "target_language": "zh-CN",
        },
        headers={"Idempotency-Key": "cancel-job"},
    ).json()
    cancelled = api.post(f"/api/v1/translation-jobs/{created['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["state"] == "cancelled"
    repeated = api.post(f"/api/v1/translation-jobs/{created['id']}/cancel")
    assert repeated.status_code == 200
    retried = api.post(f"/api/v1/translation-jobs/{created['id']}/retry")
    assert retried.status_code == 202
    assert retried.json()["state"] == "queued"
    assert retried.json()["id"] != created["id"]


def test_human_correction_uses_optimistic_lock(translation_context):
    api, document_id, factory, anchor = translation_context

    async def seed_revision():
        from app.modules.medical_translation.model import TranslationRevision

        async with factory() as session:
            revision = TranslationRevision.synthetic_for_test(
                document_id=document_id,
                source_anchor_id=anchor["id"],
                source_text_hash=anchor["quote_hash"],
                translated_text="剂量为 5 mg。",
            )
            session.add(revision)
            await session.commit()
            await session.refresh(revision)
            return revision.id

    revision_id = asyncio.run(seed_revision())
    response = api.post(
        f"/api/v1/translation-revisions/{revision_id}/corrections",
        json={
            "expected_version": 1,
            "translated_text": "剂量是 5 mg。",
            "reason": "措辞修订",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["origin"] == "human"
    assert response.json()["version"] == 2
    stale = api.post(
        f"/api/v1/translation-revisions/{revision_id}/corrections",
        json={"expected_version": 1, "translated_text": "另一个版本"},
    )
    assert stale.status_code == 409


def test_document_term_override_is_scoped_and_updatable(translation_context):
    api, document_id, _, _ = translation_context
    url = f"/api/v1/documents/{document_id}/translation-term-overrides"
    first = api.post(url, json={"source_term": "XYZ", "target_term": "自定义术语"})
    assert first.status_code == 201, first.text
    assert first.json()["scope"] == "document"
    changed = api.post(url, json={"source_term": "xyz", "target_term": "更新后的术语"})
    assert changed.status_code == 201
    entries = api.get(url)
    assert entries.status_code == 200
    assert len(entries.json()) == 1
    assert entries.json()[0]["id"] == changed.json()["id"]
    assert entries.json()[0]["source_term"] == "xyz"
    assert entries.json()[0]["target_term"] == "更新后的术语"


def test_segment_intent_uses_current_versions_and_deduplicates(translation_context):
    api, document_id, _, source_anchor = translation_context
    payload = {
        "expected_file_hash": source_anchor["file_hash"],
        "expected_anchor_revision_id": source_anchor["anchor_revision_id"],
        "expected_segmentation_revision_id": 1,
        "segment_ids": [1],
        "active_segment_id": 1,
        "trigger": "follow",
    }
    first = api.post(f"/api/v1/documents/{document_id}/translation-segment-intents", json=payload)
    assert first.status_code == 202, first.text
    assert first.json()["items"][0]["state"] in {"queued", "degraded"}
    second = api.post(f"/api/v1/documents/{document_id}/translation-segment-intents", json=payload)
    assert second.status_code == 202, second.text
    assert second.json()["deduplicated_count"] == 1


def test_current_model_blocked_segment_is_stable_and_not_requeued(translation_context):
    api, document_id, factory, source_anchor = translation_context
    payload = {
        "expected_file_hash": source_anchor["file_hash"],
        "expected_anchor_revision_id": source_anchor["anchor_revision_id"],
        "expected_segmentation_revision_id": 1,
        "segment_ids": [1],
        "active_segment_id": 1,
        "trigger": "visible",
    }
    created = api.post(
        f"/api/v1/documents/{document_id}/translation-segment-intents", json=payload
    ).json()

    async def block_current_result() -> None:
        from app.modules.medical_translation.model import TranslationRevision

        async with factory() as session:
            job = await session.get(MedicalTranslationJob, created["items"][0]["job"]["id"])
            assert job is not None
            revision = TranslationRevision.synthetic_for_test(
                document_id=document_id,
                source_anchor_id=job.source_anchor_id,
                source_text_hash=job.source_text_hash,
                translated_text="受质量门禁拦截的当前结果",
            )
            revision.job_id = job.id
            revision.provider = "ollama-local"
            revision.model = "qwen3:8b"
            revision.quality_status = "blocked"
            session.add(revision)
            await session.flush()
            job.state = "succeeded"
            job.result_revision_id = revision.id
            await session.commit()

    asyncio.run(block_current_result())
    repeated = api.post(
        f"/api/v1/documents/{document_id}/translation-segment-intents", json=payload
    )

    assert repeated.status_code == 202, repeated.text
    assert repeated.json()["queued_count"] == 0
    assert repeated.json()["deduplicated_count"] == 1
    assert repeated.json()["items"][0]["state"] == "cached"
    assert repeated.json()["items"][0]["revision"]["quality_status"] == "blocked"


def test_segment_intent_rejects_stale_versions(translation_context):
    api, document_id, _, source_anchor = translation_context
    response = api.post(f"/api/v1/documents/{document_id}/translation-segment-intents", json={
        "expected_file_hash": "f" * 64,
        "expected_anchor_revision_id": source_anchor["anchor_revision_id"],
        "expected_segmentation_revision_id": 1,
        "segment_ids": [1],
    })
    assert response.status_code == 409


def test_legacy_oversized_segment_degrades_without_crashing_request(translation_context):
    api, document_id, factory, source_anchor = translation_context

    async def make_legacy_segment_oversized() -> None:
        from app.modules.document_layout.model import DocumentLayoutSegment

        async with factory() as session:
            segment = await session.get(DocumentLayoutSegment, 1)
            assert segment is not None
            segment.text = "A" * 8_001
            await session.commit()

    asyncio.run(make_legacy_segment_oversized())
    response = api.post(f"/api/v1/documents/{document_id}/translation-segment-intents", json={
        "expected_file_hash": source_anchor["file_hash"],
        "expected_anchor_revision_id": source_anchor["anchor_revision_id"],
        "expected_segmentation_revision_id": 1,
        "segment_ids": [1],
        "trigger": "prefetch",
    })

    assert response.status_code == 202, response.text
    assert response.json()["items"][0]["state"] == "degraded"
    assert response.json()["items"][0]["degraded_reason"] == "segment_exceeds_translation_limits"
