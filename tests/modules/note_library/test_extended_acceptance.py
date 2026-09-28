"""NB-02 and NB-09 through NB-19 extended backend acceptance."""

import hashlib
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

from app.modules.document.model import Document
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.note_library.errors import NoteLibraryError
from app.modules.note_library.model import NoteDerivation
from app.modules.note_library.schema import (
    AISuggestionAdopt,
    AISuggestionComplete,
    AISuggestionCreate,
    DerivationCreate,
    DraftUpdate,
    ExportRequest,
    MetadataPatch,
    NoteCreate,
    RevisionCommit,
    SourceInput,
)
from app.modules.note_library.service import NoteLibraryService
from app.modules.research_context.model import ResearchContext
from tests.modules.note_library.helpers import create_committed_note

ACTOR = "user:extended"


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def enqueue(self, suggestion_id: int, input_text: str) -> None:
        self.calls += 1


async def source_fixture(session):
    source = KnowledgeSource(
        name="Local",
        source_type="folder",
        root_path="X:/test",
        normalized_root_path="x:/test",
        enabled=True,
    )
    session.add(source)
    await session.flush()
    document = Document(
        knowledge_source_id=source.id,
        file_path="X:/test/a.pdf",
        normalized_file_path="x:/test/a.pdf",
        file_hash="a" * 64,
        file_size=100,
        modified_time=datetime.now(UTC),
        modified_time_ns=1,
    )
    session.add(document)
    await session.flush()
    revision = DocumentAnchorRevision(
        document_id=document.id,
        file_hash=document.file_hash,
        request_fingerprint="r" * 64,
        extraction_fingerprint="e" * 64,
        extractor_version="test",
        pdfjs_version="test",
        normalization_version="test",
        options_hash="o" * 64,
        state="ready",
    )
    session.add(revision)
    await session.flush()
    quote = "Verified source quote"
    anchor = DocumentSourceAnchor(
        anchor_revision_id=revision.id,
        anchor_type="text",
        quote=quote,
        normalized_quote=quote,
        quote_hash=hashlib.sha256(quote.encode()).hexdigest(),
        content_fingerprint="f" * 64,
        quality_status="eligible",
        resolution_status="exact",
    )
    session.add(anchor)
    await session.flush()
    return source, document, revision, anchor


async def test_nb02_keyword_tag_research_intersection_and_self_excluding_facets(
    note_factory,
):
    async with note_factory() as session:
        context_a = ResearchContext(name="Study A", description="")
        context_b = ResearchContext(name="Study B", description="")
        session.add_all([context_a, context_b])
        await session.flush()
        service = NoteLibraryService(session)
        first, _ = await create_committed_note(
            session, actor=ACTOR, title="Mechanism alpha", body="target", key="q1"
        )
        second, _ = await create_committed_note(
            session, actor=ACTOR, title="Mechanism beta", body="target", key="q2"
        )
        third, _ = await create_committed_note(
            session, actor=ACTOR, title="Unrelated", body="other", key="q3"
        )
        await service.patch_metadata(
            first,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=1,
                tags=["red"],
                research_context_ids=[context_a.id],
            ),
        )
        await service.patch_metadata(
            second,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=1,
                tags=["blue"],
                research_context_ids=[context_a.id],
            ),
        )
        await service.patch_metadata(
            third,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=1,
                tags=["red"],
                research_context_ids=[context_b.id],
            ),
        )
        result = await service.list_notes(
            ACTOR,
            query="mechanism",
            tags=["red", "blue"],
            research_context_ids=[context_a.id],
        )
        assert {item.id for item in result.items} == {
            first,
            second,
        } and result.total == 2
        facets = await service.facets(
            ACTOR, query="mechanism", tags=["red"], research_context_ids=[context_a.id]
        )
        assert {item.name: item.count for item in facets.tags} == {"blue": 1, "red": 1}
        assert {item.name: item.count for item in facets.research_contexts}[
            "Study A"
        ] == 1


async def test_nb09_zero_and_multiple_typed_sources_and_forged_quote_rejection(
    note_factory,
):
    async with note_factory() as session:
        _, document, _, anchor = await source_fixture(session)
        service = NoteLibraryService(session)
        zero = await service.create(
            NoteCreate(actor_scope=ACTOR, title="Zero", body="No sources")
        )
        await service.commit(
            zero.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="zero",
            ),
        )
        note = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="Multi",
                body="Sources",
                sources=[
                    SourceInput(
                        source_type="document",
                        source_id=document.id,
                        document_id=document.id,
                        title="Bibliographic",
                    ),
                    SourceInput(
                        source_type="anchor",
                        anchor_id=anchor.id,
                        quote=anchor.quote,
                        title="Exact",
                    ),
                ],
            )
        )
        revision = await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="multi",
            ),
        )
        assert [item.granularity for item in revision.sources] == [
            "bibliographic",
            "exact_anchor",
        ]
        forged = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="Bad",
                body="Quote",
                sources=[
                    SourceInput(
                        source_type="anchor", anchor_id=anchor.id, quote="forged"
                    )
                ],
            )
        )
        with pytest.raises(NoteLibraryError) as caught:
            await service.commit(
                forged.id,
                RevisionCommit(
                    actor_scope=ACTOR,
                    expected_base_revision=0,
                    expected_draft_version=1,
                    idempotency_key="bad",
                ),
            )
        assert caught.value.code == "SOURCE_QUOTE_MISMATCH"


async def test_nb10_source_version_change_marks_review_without_rewriting_history(
    note_factory,
):
    async with note_factory() as session:
        _, document, _, anchor = await source_fixture(session)
        service = NoteLibraryService(session)
        note = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="Version",
                body="Body",
                sources=[
                    SourceInput(
                        source_type="anchor", anchor_id=anchor.id, quote=anchor.quote
                    )
                ],
            )
        )
        committed = await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="version",
            ),
        )
        original_quote = committed.sources[0].quote
        document.file_hash = "b" * 64
        read = await service.read(note.id, ACTOR)
        assert read.sources[0].status == "review_required"
        assert read.sources[0].quote == original_quote == anchor.quote


async def test_nb11_revocation_filters_detail_search_export_and_ai_input(note_factory):
    async with note_factory() as session:
        source, _, _, anchor = await source_fixture(session)
        provider = CountingProvider()
        service = NoteLibraryService(session, provider)
        note = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="Private",
                body="Own body",
                sources=[
                    SourceInput(
                        source_type="anchor",
                        anchor_id=anchor.id,
                        quote=anchor.quote,
                        title="Secret metadata",
                    )
                ],
            )
        )
        await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="private",
            ),
        )
        source.enabled = False
        detail = await service.read(note.id, ACTOR)
        assert (
            detail.sources[0].status == "access_revoked"
            and detail.sources[0].quote is None
            and detail.sources[0].title == "Restricted source"
        )
        search = await service.list_notes(ACTOR, query="Secret metadata")
        assert search.total == 0
        exported = await service.export(
            ExportRequest(actor_scope=ACTOR, note_id=note.id, format="json")
        )
        assert (
            anchor.quote not in exported.content
            and "Secret metadata" not in exported.content
        )
        suggestion = await service.create_suggestion(
            note.id,
            AISuggestionCreate(
                actor_scope=ACTOR,
                operation="polish",
                input_revision=1,
                cloud_consent=True,
            ),
        )
        assert suggestion.status == "queued" and provider.calls == 1


async def test_nb12_multiple_context_links_unlink_without_permission_expansion(
    note_factory,
):
    async with note_factory() as session:
        source, _, _, anchor = await source_fixture(session)
        first = ResearchContext(name="One", description="")
        second = ResearchContext(name="Two", description="")
        session.add_all([first, second])
        await session.flush()
        service = NoteLibraryService(session)
        note = await service.create(
            NoteCreate(
                actor_scope=ACTOR,
                title="Contexts",
                body="Body",
                sources=[
                    SourceInput(
                        source_type="anchor", anchor_id=anchor.id, quote=anchor.quote
                    )
                ],
            )
        )
        await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="contexts",
            ),
        )
        linked = await service.patch_metadata(
            note.id,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=1,
                research_context_ids=[first.id, second.id],
            ),
        )
        assert linked.research_context_ids == [first.id, second.id]
        unlinked = await service.patch_metadata(
            note.id,
            MetadataPatch(
                actor_scope=ACTOR,
                expected_metadata_version=2,
                research_context_ids=[second.id],
            ),
        )
        source.enabled = False
        denied = await service.read(note.id, ACTOR)
        assert (
            unlinked.current_revision == 1
            and denied.sources[0].status == "access_revoked"
        )


async def test_nb13_core_crud_and_search_do_not_touch_model_provider(note_factory):
    async with note_factory() as session:
        provider = CountingProvider()
        service = NoteLibraryService(session, provider)
        note = await service.create(
            NoteCreate(actor_scope=ACTOR, title="Offline", body="Core works")
        )
        await service.commit(
            note.id,
            RevisionCommit(
                actor_scope=ACTOR,
                expected_base_revision=0,
                expected_draft_version=1,
                idempotency_key="offline",
            ),
        )
        result = await service.list_notes(ACTOR, query="Core")
        assert result.total == 1 and provider.calls == 0


async def test_nb14_stale_ai_suggestion_cannot_overwrite_new_draft(note_factory):
    async with note_factory() as session:
        service = NoteLibraryService(session, CountingProvider())
        note = await service.create(
            NoteCreate(actor_scope=ACTOR, title="AI", body="old")
        )
        suggestion = await service.create_suggestion(
            note.id,
            AISuggestionCreate(
                actor_scope=ACTOR,
                operation="polish",
                input_draft_version=1,
                cloud_consent=True,
            ),
        )
        await service.update_draft(
            note.id,
            DraftUpdate(
                actor_scope=ACTOR,
                expected_draft_version=1,
                title="AI",
                body="new",
                sources=[],
            ),
        )
        completed = await service.complete_suggestion(
            suggestion.id, AISuggestionComplete(body="model output")
        )
        assert completed.is_stale
        with pytest.raises(NoteLibraryError):
            await service.adopt_suggestion(
                suggestion.id,
                AISuggestionAdopt(actor_scope=ACTOR, expected_draft_version=2),
            )
        assert (await service.get_draft(note.id, ACTOR)).body == "new"


async def test_nb14_ai_fake_boundary_tracks_lifecycle_timeout_and_cancel(note_factory):
    async with note_factory() as session:
        service = NoteLibraryService(session, CountingProvider())
        note = await service.create(
            NoteCreate(actor_scope=ACTOR, title="AI", body="draft")
        )
        queued = await service.create_suggestion(
            note.id,
            AISuggestionCreate(
                actor_scope=ACTOR,
                operation="polish",
                input_draft_version=1,
                cloud_consent=True,
            ),
        )
        running = await service.start_suggestion(queued.id)
        timed_out = await service.timeout_suggestion(queued.id)
        assert (queued.status, running.status, timed_out.status) == (
            "queued",
            "running",
            "failed",
        )
        cancelled = await service.create_suggestion(
            note.id,
            AISuggestionCreate(
                actor_scope=ACTOR,
                operation="title",
                input_draft_version=1,
                cloud_consent=True,
            ),
        )
        stopped = await service.cancel_suggestion(cancelled.id, ACTOR)
        late = await service.complete_suggestion(
            cancelled.id, AISuggestionComplete(title="late result")
        )
        assert stopped.status == late.status == "cancelled"
        assert (await service.get_draft(note.id, ACTOR)).body == "draft"


async def test_nb15_cloud_consent_rejects_before_provider_call(note_factory):
    async with note_factory() as session:
        provider = CountingProvider()
        service = NoteLibraryService(session, provider)
        note = await service.create(NoteCreate(actor_scope=ACTOR))
        with pytest.raises(NoteLibraryError) as caught:
            await service.create_suggestion(
                note.id,
                AISuggestionCreate(
                    actor_scope=ACTOR,
                    operation="title",
                    input_draft_version=1,
                    cloud_consent=False,
                ),
            )
        assert caught.value.code == "CLOUD_CONSENT_REQUIRED" and provider.calls == 0


async def test_nb16_derivation_is_idempotent_and_pins_revision(note_factory):
    async with note_factory() as session:
        note_id, revision_id = await create_committed_note(session, actor=ACTOR)
        service = NoteLibraryService(session)
        payload = DerivationCreate(
            actor_scope=ACTOR,
            revision_no=1,
            target_type="writing",
            idempotency_key="derive",
        )
        first = await service.derive(note_id, payload)
        second = await service.derive(note_id, payload)
        assert first.id == second.id and first.revision_id == revision_id
        assert (
            await session.scalar(select(func.count()).select_from(NoteDerivation)) == 1
        )
        with pytest.raises(NoteLibraryError) as caught:
            await service.derive(
                note_id,
                DerivationCreate(
                    actor_scope=ACTOR,
                    revision_no=1,
                    target_type="claim",
                    idempotency_key="claim",
                ),
            )
        assert caught.value.code == "TARGET_CAPABILITY_UNAVAILABLE"


async def test_nb17_malicious_markdown_url_is_safe_in_preview_and_export(note_factory):
    async with note_factory() as session:
        body = "<script>alert(1)</script> [bad](javascript:alert(2)) [good](https://example.test) ![remote](https://tracker.test/x)"
        note_id, _ = await create_committed_note(
            session, actor=ACTOR, title="../Bad:*Name", body=body
        )
        service = NoteLibraryService(session)
        detail = await service.read(note_id, ACTOR)
        exported = await service.export(
            ExportRequest(actor_scope=ACTOR, note_id=note_id, format="markdown")
        )
        assert (
            "<script" not in detail.body
            and "javascript:" not in detail.body
            and "![remote]" not in detail.body
        )
        assert (
            "/" not in exported.filename
            and "\\" not in exported.filename
            and "javascript:" not in exported.content
        )


async def test_nb19_backend_contract_exposes_workflow_state_and_capabilities(
    note_factory,
):
    async with note_factory() as session:
        note = await NoteLibraryService(session).create(NoteCreate(actor_scope=ACTOR))
        detail = await NoteLibraryService(session).read(note.id, ACTOR)
        draft = await NoteLibraryService(session).get_draft(note.id, ACTOR)
        listed = await NoteLibraryService(session).list_notes(ACTOR)
        assert {"edit", "save_revision", "archive", "export"}.issubset(
            detail.capabilities
        )
        assert {"local_actor_scope_only", "ai_suggestions_unavailable"}.issubset(
            detail.capabilities
        )
        assert draft.save_state == "draft_saved" and draft.draft_version == 1
        assert listed.query_fingerprint and listed.as_of
