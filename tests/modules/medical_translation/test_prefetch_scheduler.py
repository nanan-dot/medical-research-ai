import asyncio

from sqlalchemy import select

from app.modules.medical_translation.model import MedicalTranslationJob
from app.modules.medical_translation.prefetch import (
    DocumentTranslationPrefetchScheduler,
)
from tests.modules.medical_translation.test_api import (
    client,
    selection_client,
    translation_context,
)

__all__ = ["client", "selection_client", "translation_context"]


def test_ready_document_segments_are_queued_for_background_translation(
    translation_context,
):
    _, document_id, factory, _ = translation_context

    async def exercise():
        scheduler = DocumentTranslationPrefetchScheduler(factory)
        assert await scheduler.run_once() is True
        async with factory() as session:
            return list(
                (
                    await session.scalars(
                        select(MedicalTranslationJob).where(
                            MedicalTranslationJob.document_id == document_id,
                            MedicalTranslationJob.request_trigger == "prefetch",
                        )
                    )
                ).all()
            )

    jobs = asyncio.run(exercise())
    assert jobs
    assert all(job.layout_segment_id is not None for job in jobs)
    assert all(job.request_priority == 1 for job in jobs)
