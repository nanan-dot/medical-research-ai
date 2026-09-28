"""NB-18 legacy reading-note backfill acceptance."""

from app.modules.document_selection.model import DocumentReadingNote
from app.modules.note_library.schema import LegacyBackfillRead
from app.modules.note_library.service import NoteLibraryService
from tests.modules.note_library.test_extended_acceptance import source_fixture


async def test_nb18_dry_run_and_repeated_backfill_are_lossless_and_idempotent(
    note_factory,
):
    async with note_factory() as session:
        _, document, _, anchor = await source_fixture(session)
        legacy = DocumentReadingNote(
            document_id=document.id,
            source_anchor_id=anchor.id,
            content="Legacy body",
            quote_snapshot=anchor.quote,
        )
        session.add(legacy)
        await session.commit()
        service = NoteLibraryService(session)
        dry = await service.backfill_legacy("user:legacy", dry_run=True)
        first = await service.backfill_legacy("user:legacy", dry_run=False)
        second = await service.backfill_legacy("user:legacy", dry_run=False)
        assert dry == LegacyBackfillRead(dry_run=True, eligible=1, created=0, skipped=0)
        assert first.created == 1 and second.created == 0 and second.skipped == 1
        note = (await service.list_notes("user:legacy")).items[0]
        revision = await service.get_revision(note.id, 1, "user:legacy")
        assert (
            revision.body == "Legacy body" and revision.sources[0].quote == anchor.quote
        )
