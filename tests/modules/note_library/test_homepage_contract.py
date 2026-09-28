"""Acceptance coverage for frozen homepage list contracts."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import event, select, update

from app.modules.library_item.model import LibraryItem
from app.modules.note_library.errors import NoteLibraryError
from app.modules.note_library.model import NoteRevision, ResearchNote
from app.modules.note_library.schema import (
    DraftUpdate,
    MetadataPatch,
    NoteCreate,
    RevisionCommit,
    SourceInput,
)
from app.modules.note_library.service import NoteLibraryService
from app.modules.research_context.model import ResearchContext
from tests.modules.note_library.test_extended_acceptance import ACTOR, source_fixture


async def test_homepage_views_counts_and_list_summaries(note_factory):
    async with note_factory() as session:
        _, document, _, _ = await source_fixture(session)
        context = ResearchContext(name="CKD study", description="")
        session.add(context)
        await session.flush()
        service = NoteLibraryService(session)
        note = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="Recent",
                body="body",
                sources=[SourceInput(source_type="document", source_id=document.id)],
            )
        )
        await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="recent",
            ),
        )
        await service.patch_metadata(
            note.id,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=1,
                research_context_ids=[context.id],
            ),
        )
        unlinked = await service.create(
            NoteCreate(actor_scope=ACTOR, title="Unlinked", body="body")
        )
        await service.commit(
            unlinked.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="unlinked",
            ),
        )
        await session.execute(
            update(ResearchNote)
            .where(ResearchNote.id == unlinked.id)
            .values(content_updated_at=datetime.now(UTC) - timedelta(days=31))
        )
        recent = await service.list_notes(ACTOR, view="recent")
        only_unlinked = await service.list_notes(ACTOR, view="unlinked_research")
        facets = await service.facets(ACTOR)
        assert [item.id for item in recent.items] == [note.id]
        assert [item.id for item in only_unlinked.items] == [unlinked.id]
        assert recent.items[0].source_summaries[0].title
        assert recent.items[0].research_context_summaries[0].name == "CKD study"
        assert facets.quick_counts["recent"] == 1


async def test_non_anchor_sources_are_server_resolved_and_reject_forgery(note_factory):
    async with note_factory() as session:
        _, document, _, anchor = await source_fixture(session)
        paper = LibraryItem(
            title="Trusted paper", fulltext_status="none", fulltext_status_reason=""
        )
        session.add(paper)
        await session.flush()
        service = NoteLibraryService(session)
        note = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="sources",
                body="body",
                sources=[
                    SourceInput(
                        source_type="document", source_id=document.id, title="forged"
                    )
                ],
            )
        )
        revision = await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="trusted-document",
            ),
        )
        assert revision.sources[0].title != "forged"
        anchored = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="anchor",
                body="body",
                sources=[
                    SourceInput(
                        source_type="anchor",
                        anchor_id=anchor.id,
                        quote=anchor.quote,
                        title="forged anchor title",
                    )
                ],
            )
        )
        anchor_revision = await service.commit(
            anchored.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="trusted-anchor",
            ),
        )
        assert anchor_revision.sources[0].title != "forged anchor title"
        bad = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="bad",
                body="body",
                sources=[SourceInput(source_type="paper", source_id=999)],
            )
        )
        with pytest.raises(NoteLibraryError) as caught:
            await service.commit(
                bad.id,
                RevisionCommit(
                    actor_scope=ACTOR,
                    expected_base_revision=0,
                    expected_draft_version=1,
                    idempotency_key="wrong-type",
                ),
            )
        assert caught.value.code == "SOURCE_UNAVAILABLE"


async def test_history_is_bounded_and_paginated(note_factory):
    async with note_factory() as session:
        service = NoteLibraryService(session)
        note = await service.create(
            NoteCreate(actor_scope=ACTOR, title="v1", body="body")
        )
        for number in range(3):
            draft = await service.get_draft(note.id, ACTOR)
            if number:
                await service.update_draft(
                    note.id,
                    DraftUpdate(
                        actor_scope=ACTOR,
                        expected_draft_version=draft.draft_version,
                        title=f"v{number + 1}",
                        body=draft.body,
                        sources=draft.sources,
                    ),
                )
                draft = await service.get_draft(note.id, ACTOR)
            await service.commit(
                note.id,
                RevisionCommit(
                    actor_scope=ACTOR,
                    expected_base_revision=number,
                    expected_draft_version=draft.draft_version,
                    idempotency_key=f"v{number}",
                ),
            )
        history = await service.revision_history(note.id, ACTOR, page=2, page_size=2)
        assert history.total == 3 and [item.revision_no for item in history.items] == [
            1
        ]


async def test_1000_note_page_uses_bounded_query_count(note_factory):
    async with note_factory() as session:
        session.add_all(
            [ResearchNote(owner_scope=ACTOR, current_revision=1) for _ in range(1000)]
        )
        await session.flush()
        notes = list(
            await session.scalars(
                select(ResearchNote).where(ResearchNote.owner_scope == ACTOR)
            )
        )
        session.add_all(
            [
                NoteRevision(
                    note_id=note.id,
                    revision_no=1,
                    title=f"N{note.id}",
                    body="body",
                )
                for note in notes
            ]
        )
        await session.flush()
        statements: list[str] = []

        def record_statement(*args: object) -> None:
            statements.append(str(args[2]))

        engine = session.sync_session.bind
        assert engine is not None
        event.listen(engine, "before_cursor_execute", record_statement)
        try:
            page = await NoteLibraryService(session).list_notes(
                ACTOR, page=5, page_size=100
            )
        finally:
            event.remove(engine, "before_cursor_execute", record_statement)
        assert page.total == 1000 and len(page.items) == 100
        assert len(statements) <= 8
