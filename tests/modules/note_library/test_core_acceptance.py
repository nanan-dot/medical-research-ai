"""NB-01 through NB-08 and NB-20 core persistence acceptance."""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, update

from app.modules.note_library.errors import NoteLibraryError
from app.modules.note_library.model import NoteDraft, NoteRevision, ResearchNote
from app.modules.note_library.schema import (
    DraftUpdate,
    MetadataPatch,
    NoteCreate,
    RestoreRequest,
    RevisionCommit,
)
from app.modules.note_library.service import NoteLibraryService
from tests.modules.note_library.helpers import create_committed_note

ACTOR = "user:alpha"


async def test_nb01_independent_note_and_draft_persist_across_sessions(note_factory):
    async with note_factory() as session:
        note = await NoteLibraryService(session).create(NoteCreate(actor_scope=ACTOR))
        await session.commit()
        note_id = note.id
    async with note_factory() as session:
        draft = await NoteLibraryService(session).get_draft(note_id, ACTOR)
        assert draft.title == "" and draft.body == "" and draft.base_revision == 0


async def test_nb07_autosave_and_formal_revision_are_separate(note_factory):
    async with note_factory() as session:
        service = NoteLibraryService(session)
        note = await service.create(NoteCreate(actor_scope=ACTOR))
        draft = await service.update_draft(
            note.id,
            DraftUpdate(
                actor_scope=ACTOR,
                expected_draft_version=1,
                title="Draft",
                body="Text",
                sources=[],
            ),
        )
        assert draft.draft_version == 2
        assert await session.scalar(select(func.count()).select_from(NoteRevision)) == 0
        revision = await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=2,
                idempotency_key="formal",
            ),
        )
        assert revision.revision_no == 1


async def test_formal_revision_refreshes_content_updated_at(note_factory):
    stale_time = datetime(2000, 1, 1, tzinfo=UTC)
    async with note_factory() as session:
        service = NoteLibraryService(session)
        note = await service.create(NoteCreate(actor_scope=ACTOR, title="A", body="B"))
        await session.execute(
            update(ResearchNote)
            .where(ResearchNote.id == note.id)
            .values(content_updated_at=stale_time)
        )
        await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="refresh-content-time",
            ),
        )
        entity = await session.get(ResearchNote, note.id)
        assert entity is not None and entity.content_updated_at.year > stale_time.year


async def test_nb06_idempotent_save_replays_and_rejects_changed_request(note_factory):
    async with note_factory() as session:
        service = NoteLibraryService(session)
        note = await service.create(NoteCreate(actor_scope=ACTOR, title="A", body="B"))
        payload = RevisionCommit(
            actor_scope=ACTOR,
            expected_base_revision=0,
            expected_draft_version=1,
            idempotency_key="same",
        )
        first = await service.commit(note.id, payload)
        second = await service.commit(note.id, payload)
        assert first.id == second.id
        draft_entity = await service.repository.draft(note.id, ACTOR)
        assert draft_entity is not None
        draft_entity.body = "changed"
        with pytest.raises(NoteLibraryError, match="reused") as caught:
            await service.commit(note.id, payload)
        assert caught.value.code == "IDEMPOTENCY_KEY_REUSED"


async def test_nb04_metadata_archive_roundtrip_does_not_create_revision(note_factory):
    async with note_factory() as session:
        note_id, _ = await create_committed_note(session, actor=ACTOR)
        service = NoteLibraryService(session)
        changed = await service.patch_metadata(
            note_id,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=1,
                is_favorite=True,
                tags=["Mechanism"],
            ),
        )
        assert changed.current_revision == 1 and changed.is_favorite
        archived = await service.archive(note_id, ACTOR, True)
        assert archived.is_archived and archived.current_revision == 1
        await service.archive(note_id, ACTOR, False)
        await session.commit()
    async with note_factory() as session:
        read = await NoteLibraryService(session).read(note_id, ACTOR)
        assert read.is_favorite and not read.is_archived and read.current_revision == 1
        assert (
            await NoteLibraryService(session).revision_history(note_id, ACTOR)
        ).total == 1


async def test_nb08_restore_adds_revision_and_preserves_old_identity(note_factory):
    async with note_factory() as session:
        note_id, first_revision_id = await create_committed_note(
            session, actor=ACTOR, title="Old", body="One"
        )
        service = NoteLibraryService(session)
        draft = await service.get_draft(note_id, ACTOR)
        await service.update_draft(
            note_id,
            DraftUpdate(
                actor_scope=ACTOR,
                expected_draft_version=draft.draft_version,
                title="New",
                body="Two",
                sources=[],
            ),
        )
        current = await service.get_draft(note_id, ACTOR)
        await service.commit(
            note_id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=1,
                expected_draft_version=current.draft_version,
                idempotency_key="save-2",
            ),
        )
        restored = await service.restore(
            note_id,
            RestoreRequest(
                actor_scope=ACTOR,
                revision_no=1,
                expected_base_revision=2,
                idempotency_key="restore",
            ),
        )
        old = await service.get_revision(note_id, 1, ACTOR)
        assert restored.revision_no == 3 and restored.restored_from_revision == 1
        assert old.id == first_revision_id and old.title == "Old"


async def test_restore_rejects_a_draft_changed_before_its_cas_write(
    note_factory, monkeypatch
):
    async with note_factory() as session:
        note_id, _ = await create_committed_note(
            session, actor=ACTOR, title="Old", body="One"
        )
        service = NoteLibraryService(session)
        draft = await service.get_draft(note_id, ACTOR)
        await service.update_draft(
            note_id,
            DraftUpdate(
                actor_scope=ACTOR,
                expected_draft_version=draft.draft_version,
                title="New",
                body="Two",
                sources=[],
            ),
        )
        latest = await service.get_draft(note_id, ACTOR)
        await service.commit(
            note_id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=1,
                expected_draft_version=latest.draft_version,
                idempotency_key="save-new",
            ),
        )
        original_cas = service.repository.cas_draft

        async def competing_cas(
            draft_id: int, expected_version: int, **values: object
        ) -> bool:
            await session.execute(
                update(NoteDraft)
                .where(
                    NoteDraft.id == draft_id,
                    NoteDraft.draft_version == expected_version,
                )
                .values(draft_version=expected_version + 1, body="latest draft")
            )
            return await original_cas(draft_id, expected_version, **values)

        monkeypatch.setattr(service.repository, "cas_draft", competing_cas)
        with pytest.raises(NoteLibraryError) as caught:
            await service.restore(
                note_id,
                RestoreRequest(
                    actor_scope=ACTOR,
                    revision_no=1,
                    expected_base_revision=2,
                    idempotency_key="restore-race",
                ),
            )
        assert caught.value.code == "NOTE_DRAFT_VERSION_CONFLICT"
        assert (await service.get_draft(note_id, ACTOR)).body == "latest draft"


async def test_nb05_two_real_sessions_allow_one_cas_winner_and_preserve_draft(
    note_factory,
):
    async with note_factory() as setup:
        service = NoteLibraryService(setup)
        note = await service.create(
            NoteCreate(actor_scope=ACTOR, title="Race", body="Body")
        )
        await setup.commit()
        note_id = note.id

    ready = asyncio.Event()
    arrivals = 0
    lock = asyncio.Lock()

    async def submit(key: str):
        nonlocal arrivals
        async with note_factory() as session:
            service = NoteLibraryService(session)
            await service.get_draft(note_id, ACTOR)
            async with lock:
                arrivals += 1
                if arrivals == 2:
                    ready.set()
            await ready.wait()
            try:
                result = await service.commit(
                    note_id,
                    RevisionCommit(
                        actor_scope=ACTOR,
                        expected_base_revision=0,
                        expected_draft_version=1,
                        idempotency_key=key,
                    ),
                )
                await session.commit()
                return result.revision_no
            except NoteLibraryError as error:
                await session.rollback()
                return error.code

    outcomes = await asyncio.gather(submit("race-a"), submit("race-b"))
    assert sorted(map(str, outcomes)) == ["1", "NOTE_VERSION_CONFLICT"]
    async with note_factory() as session:
        draft = await NoteLibraryService(session).get_draft(note_id, ACTOR)
        assert draft.title == "Race" and draft.body == "Body"


async def test_nb03_500_equal_timestamp_notes_have_stable_bounded_pages(note_factory):
    same_time = datetime(2026, 1, 1, tzinfo=UTC)
    async with note_factory() as session:
        for index in range(500):
            await create_committed_note(
                session,
                actor=ACTOR,
                title=f"N{index:03d}",
                body="stable",
                key=f"key-{index}",
            )
        await session.execute(update(ResearchNote).values(content_updated_at=same_time))
        await session.commit()
    async with note_factory() as session:
        service = NoteLibraryService(session)
        page1 = await service.list_notes(ACTOR, page=1, page_size=100)
        page5 = await service.list_notes(ACTOR, page=5, page_size=100)
        beyond = await service.list_notes(ACTOR, page=6, page_size=100)
        assert page1.total == page5.total == beyond.total == 500
        assert [item.id for item in page1.items] == sorted(
            (item.id for item in page1.items), reverse=True
        )
        assert len(page5.items) == 100 and beyond.items == []
        with pytest.raises(NoteLibraryError):
            await service.list_notes(ACTOR, page=0, page_size=20)


async def test_nb20_stale_autosave_is_rejected_without_losing_latest_draft(
    note_factory,
):
    async with note_factory() as session:
        service = NoteLibraryService(session)
        note = await service.create(NoteCreate(actor_scope=ACTOR))
        await service.update_draft(
            note.id,
            DraftUpdate(
                actor_scope=ACTOR,
                expected_draft_version=1,
                title="Latest",
                body="kept",
                sources=[],
            ),
        )
        with pytest.raises(NoteLibraryError) as caught:
            await service.update_draft(
                note.id,
                DraftUpdate(
                    actor_scope=ACTOR,
                    expected_draft_version=1,
                    title="Old response",
                    body="stale",
                    sources=[],
                ),
            )
        assert caught.value.code == "NOTE_DRAFT_VERSION_CONFLICT"
        latest = await service.get_draft(note.id, ACTOR)
        assert (latest.title, latest.body, latest.draft_version) == (
            "Latest",
            "kept",
            2,
        )
