import asyncio

import pytest
from sqlalchemy import select

from app.modules.medical_translation.model import (
    MedicalTranslationJob,
    TranslationRevision,
)
from app.modules.medical_translation.provider import TranslationProviderResult
from app.modules.medical_translation.service import MedicalTranslationService
from app.modules.medical_translation.worker import MedicalTranslationWorker
from app.modules.task.model import TaskRecord
from tests.modules.document_annotation.test_document_annotation_api import client
from tests.modules.document_selection.test_api import selection_client

__all__ = ["client", "selection_client"]


class SafeFakeProvider:
    async def translate(
        self,
        *,
        source_text: str,
        source_language: str,
        target_language: str,
        glossary: dict[str, str] | None = None,
    ):
        del source_language, target_language, glossary
        translated = "剂量为 5 mg"
        return TranslationProviderResult(
            translated_text=translated,
            alignment=[
                {
                    "source_start": 0,
                    "source_end": len(source_text),
                    "target_start": 0,
                    "target_end": len(translated),
                }
            ],
            provider="deterministic-fake",
            model="phase1-test",
            model_revision="1",
        )


async def fake_factory(_session):
    return SafeFakeProvider()


@pytest.fixture
def queued_translation(selection_client):
    api, document_id, factory, descriptor = selection_client
    anchor = api.post(
        f"/api/v1/documents/{document_id}/source-anchors", json=descriptor
    ).json()
    created = api.post(
        f"/api/v1/documents/{document_id}/translation-jobs",
        json={
            "source_anchor_id": anchor["id"],
            "source_language": "en",
            "target_language": "zh-CN",
        },
        headers={"Idempotency-Key": "worker-job"},
    ).json()
    return api, factory, created


def test_worker_publishes_immutable_revision_and_quality_report(queued_translation):
    api, factory, created = queued_translation
    assert (
        asyncio.run(MedicalTranslationWorker(factory, fake_factory).run_once()) is True
    )
    status = api.get(f"/api/v1/translation-jobs/{created['id']}").json()
    assert status["state"] == "succeeded"
    revision = api.get(f"/api/v1/translation-revisions/{status['result_revision_id']}")
    assert revision.status_code == 200
    payload = revision.json()
    assert payload["translated_text"] == "剂量为 5 mg"
    assert payload["quality_status"] == "machine_checked"
    assert payload["alignment"][0]["source_start"] == 0
    assert payload["provider"] == "deterministic-fake"


def test_late_provider_result_cannot_overwrite_cancellation(queued_translation):
    api, factory, created = queued_translation

    class CancellingProvider(SafeFakeProvider):
        async def translate(self, **kwargs):
            async with factory() as session:
                await MedicalTranslationService(session).cancel(created["id"])
                await session.commit()
            return await super().translate(**kwargs)

    async def cancelling_factory(_session):
        return CancellingProvider()

    asyncio.run(MedicalTranslationWorker(factory, cancelling_factory).run_once())
    status = api.get(f"/api/v1/translation-jobs/{created['id']}").json()
    assert status["state"] == "cancelled"
    assert status["result_revision_id"] is None

    async def count_revisions():
        async with factory() as session:
            return len(list((await session.scalars(select(TranslationRevision))).all()))

    assert asyncio.run(count_revisions()) == 0


def test_worker_has_finite_retry_and_safe_failure_metadata(queued_translation):
    api, factory, created = queued_translation

    class FailingProvider:
        async def translate(self, **_kwargs):
            raise RuntimeError("secret source must never be stored")

    async def failing_factory(_session):
        return FailingProvider()

    worker = MedicalTranslationWorker(factory, failing_factory)
    for _ in range(3):
        assert asyncio.run(worker.run_once()) is True
    status = api.get(f"/api/v1/translation-jobs/{created['id']}").json()
    assert status["state"] == "failed"
    assert status["attempt_count"] == 3
    assert status["error_message"] == "Medical translation did not complete"
    assert "secret" not in str(status)

    async def task_state():
        async with factory() as session:
            job = await session.get(MedicalTranslationJob, created["id"])
            task = await session.get(TaskRecord, job.task_id)
            return task.status, task.active_idempotency_key

    assert asyncio.run(task_state()) == ("failed", None)


def test_provider_initialization_failure_is_retried_safely(queued_translation):
    api, factory, created = queued_translation

    async def unavailable_factory(_session):
        raise RuntimeError("model configuration secret")

    worker = MedicalTranslationWorker(factory, unavailable_factory)
    for _ in range(3):
        assert asyncio.run(worker.run_once()) is True
    status = api.get(f"/api/v1/translation-jobs/{created['id']}").json()
    assert status["state"] == "failed"
    assert status["error_message"] == "Medical translation did not complete"
    assert "secret" not in str(status)


def test_document_term_override_is_injected_only_for_its_document(queued_translation):
    api, factory, created = queued_translation
    response = api.post(
        "/api/v1/documents/1/translation-term-overrides",
        json={"source_term": "XYZ", "target_term": "自定义术语"},
    )
    assert response.status_code == 201

    captured: list[dict[str, str] | None] = []

    class CapturingProvider(SafeFakeProvider):
        async def translate(self, *, glossary=None, **kwargs):
            captured.append(glossary)
            return await super().translate(glossary=glossary, **kwargs)

    async def capturing_factory(_session):
        return CapturingProvider()

    assert asyncio.run(MedicalTranslationWorker(factory, capturing_factory).run_once())
    assert captured == [{"xyz": "自定义术语"}]
    job = api.get(f"/api/v1/translation-jobs/{created['id']}").json()
    assert job["state"] == "succeeded"


def test_worker_claims_active_reading_priority_before_prefetch(queued_translation):
    api, factory, first = queued_translation
    created = api.post(
        "/api/v1/documents/1/translation-jobs",
        json={
            "source_anchor_id": first["source_anchor_id"],
            "source_language": "en",
            "target_language": "zh-CN",
        },
        headers={"Idempotency-Key": "worker-prefetch-job"},
    ).json()

    async def assign_priorities() -> None:
        async with factory() as session:
            prefetch = await session.get(MedicalTranslationJob, first["id"])
            active = await session.get(MedicalTranslationJob, created["id"])
            assert prefetch is not None and active is not None
            prefetch.request_priority = 1
            prefetch.request_trigger = "prefetch"
            active.request_priority = 3
            active.request_trigger = "follow"
            await session.commit()

    asyncio.run(assign_priorities())
    assert asyncio.run(MedicalTranslationWorker(factory, fake_factory).run_once())
    assert api.get(f"/api/v1/translation-jobs/{created['id']}").json()["state"] == "succeeded"
    assert api.get(f"/api/v1/translation-jobs/{first['id']}").json()["state"] == "queued"
