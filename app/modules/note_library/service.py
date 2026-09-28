"""Business rules for independent, immutable research notes."""

import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.document.model import Document
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_selection.model import DocumentReadingNote
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library_item.model import LibraryItem
from app.modules.note_library.content_safety import (
    safe_filename,
    safe_markdown,
    safe_url,
)
from app.modules.note_library.errors import NoteLibraryError
from app.modules.note_library.model import (
    NoteActivity,
    NoteAISuggestion,
    NoteDerivation,
    NoteDraft,
    NoteLegacyBackfill,
    NoteResearchLink,
    NoteRevision,
    NoteSaveOperation,
    NoteSourceLink,
    NoteTag,
    ResearchNote,
)
from app.modules.note_library.repository import NoteLibraryRepository
from app.modules.note_library.schema import (
    AISuggestionAdopt,
    AISuggestionComplete,
    AISuggestionCreate,
    AISuggestionRead,
    DerivationCreate,
    DerivationRead,
    DraftRead,
    DraftUpdate,
    ExportRead,
    ExportRequest,
    FacetsRead,
    FacetValue,
    LegacyBackfillRead,
    MetadataPatch,
    NoteCreate,
    NoteListItem,
    NoteListRead,
    NoteRead,
    ResearchContextSummary,
    RestoreRequest,
    RevisionCommit,
    RevisionHistoryRead,
    RevisionRead,
    SourceInput,
    SourceRead,
    SourceSummary,
)
from app.modules.research_context.model import ResearchContext


class AISuggestionProvider(Protocol):
    async def enqueue(self, suggestion_id: int, input_text: str) -> None: ...


class DisabledAISuggestionProvider:
    async def enqueue(self, suggestion_id: int, input_text: str) -> None:
        return None


class NoteLibraryService:
    """Coordinate domain transactions without importing HTTP concerns."""

    def __init__(
        self, session: AsyncSession, ai_provider: AISuggestionProvider | None = None
    ) -> None:
        self.session = session
        self.repository = NoteLibraryRepository(session)
        self.ai_provider = ai_provider or DisabledAISuggestionProvider()

    async def create(self, payload: NoteCreate) -> NoteRead:
        note = ResearchNote(owner_scope=payload.actor_scope)
        self.session.add(note)
        await self.session.flush()
        draft = NoteDraft(
            note_id=note.id,
            actor_scope=payload.actor_scope,
            title=payload.title,
            body=payload.body,
            sources_json=self._sources_json(payload.sources),
        )
        self.session.add_all(
            [draft, self._activity(note.id, payload.actor_scope, "created")]
        )
        await self.session.flush()
        return await self.read(note.id, payload.actor_scope)

    async def get_draft(self, note_id: int, actor_scope: str) -> DraftRead:
        await self._require_note(note_id, actor_scope)
        draft = await self.repository.draft(note_id, actor_scope)
        if draft is None:
            raise NotFoundError("Note draft not found")
        return self._draft_read(draft)

    async def update_draft(self, note_id: int, payload: DraftUpdate) -> DraftRead:
        await self._require_note(note_id, payload.actor_scope)
        draft = await self.repository.draft(note_id, payload.actor_scope)
        if draft is None:
            raise NotFoundError("Note draft not found")
        updated = await self.repository.cas_draft(
            draft.id,
            payload.expected_draft_version,
            title=payload.title,
            body=payload.body,
            sources_json=self._sources_json(payload.sources),
        )
        if not updated:
            raise NoteLibraryError(
                "NOTE_DRAFT_VERSION_CONFLICT", "Draft version has changed"
            )
        await self.session.flush()
        await self.session.refresh(draft)
        return self._draft_read(draft)

    async def commit(self, note_id: int, payload: RevisionCommit) -> RevisionRead:
        await self._require_note(note_id, payload.actor_scope)
        draft = await self.repository.draft(note_id, payload.actor_scope)
        if draft is None:
            raise NotFoundError("Note draft not found")
        request_hash = self._request_hash(payload, draft)
        previous = await self.session.scalar(
            select(NoteSaveOperation).where(
                NoteSaveOperation.actor_scope == payload.actor_scope,
                NoteSaveOperation.note_id == note_id,
                NoteSaveOperation.idempotency_key == payload.idempotency_key,
            )
        )
        if previous is not None:
            if previous.request_hash != request_hash:
                raise NoteLibraryError(
                    "IDEMPOTENCY_KEY_REUSED", "Idempotency key was reused"
                )
            revision = await self.session.get(NoteRevision, previous.revision_id)
            assert revision is not None
            return await self._revision_read(revision)
        if not draft.title.strip() or not draft.body.strip():
            raise NoteLibraryError(
                "NOTE_VALIDATION_ERROR",
                "A formal revision requires nonblank title and body",
                status_code=422,
                detail={"fields": ["title", "body"]},
            )
        if (
            draft.base_revision != payload.expected_base_revision
            or draft.draft_version != payload.expected_draft_version
        ):
            raise NoteLibraryError(
                "NOTE_VERSION_CONFLICT", "Draft base or version has changed"
            )
        if not await self.repository.cas_note_revision(
            note_id, payload.actor_scope, payload.expected_base_revision
        ):
            raise NoteLibraryError("NOTE_VERSION_CONFLICT", "Note revision has changed")
        revision = NoteRevision(
            note_id=note_id,
            revision_no=payload.expected_base_revision + 1,
            title=draft.title.strip(),
            body=draft.body,
        )
        self.session.add(revision)
        await self.session.flush()
        await self._freeze_sources(revision.id, self._parse_sources(draft.sources_json))
        draft.base_revision = revision.revision_no
        self.session.add(
            NoteSaveOperation(
                actor_scope=payload.actor_scope,
                note_id=note_id,
                idempotency_key=payload.idempotency_key,
                request_hash=request_hash,
                revision_id=revision.id,
            )
        )
        self.session.add(
            self._activity(
                note_id,
                payload.actor_scope,
                "revision_created",
                {"revision_no": revision.revision_no},
            )
        )
        await self.session.flush()
        return await self._revision_read(revision)

    async def read(self, note_id: int, actor_scope: str) -> NoteRead:
        note = await self._require_note(note_id, actor_scope)
        revision = (
            await self.repository.revision(note.id, note.current_revision)
            if note.current_revision
            else None
        )
        draft = await self.repository.draft(note.id, actor_scope)
        title = revision.title if revision else (draft.title if draft else "")
        body = revision.body if revision else (draft.body if draft else "")
        sources = await self._source_reads(revision.id) if revision else []
        return NoteRead(
            id=note.id,
            current_revision=note.current_revision,
            metadata_version=note.metadata_version,
            title=title,
            body=safe_markdown(body),
            is_favorite=note.is_favorite,
            is_archived=note.is_archived,
            tags=[item.display_name for item in await self.repository.tags(note.id)],
            research_context_ids=await self.repository.research_ids(note.id),
            sources=sources,
            capabilities=[
                "edit",
                "save_revision",
                "archive" if not note.is_archived else "unarchive",
                "export",
                "local_actor_scope_only",
                "ai_suggestions_unavailable",
            ],
            content_updated_at=note.content_updated_at,
            created_at=note.created_at,
        )

    async def revision_history(
        self, note_id: int, actor_scope: str, *, page: int = 1, page_size: int = 20
    ) -> RevisionHistoryRead:
        await self._require_note(note_id, actor_scope)
        if page < 1 or not 1 <= page_size <= 100:
            raise NoteLibraryError(
                "NOTE_QUERY_INVALID", "Invalid page or page_size", status_code=422
            )
        revisions, total = await self.repository.revision_page(
            note_id, page=page, page_size=page_size
        )
        return RevisionHistoryRead(
            items=[await self._revision_read(item) for item in revisions],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_revision(
        self, note_id: int, revision_no: int, actor_scope: str
    ) -> RevisionRead:
        await self._require_note(note_id, actor_scope)
        revision = await self.repository.revision(note_id, revision_no)
        if revision is None:
            raise NotFoundError("Note revision not found")
        return await self._revision_read(revision)

    async def restore(self, note_id: int, payload: RestoreRequest) -> RevisionRead:
        source = await self.repository.revision(note_id, payload.revision_no)
        note = await self._require_note(note_id, payload.actor_scope)
        if source is None:
            raise NotFoundError("Note revision not found")
        if note.current_revision != payload.expected_base_revision:
            raise NoteLibraryError("NOTE_VERSION_CONFLICT", "Note revision has changed")
        draft = await self.repository.draft(note_id, payload.actor_scope)
        assert draft is not None
        restored_sources = self._sources_json(
            [
                self._source_input(item)
                for item in await self.repository.sources(source.id)
            ]
        )
        restored = await self.repository.cas_draft(
            draft.id,
            draft.draft_version,
            title=source.title,
            body=source.body,
            sources_json=restored_sources,
            base_revision=note.current_revision,
        )
        if not restored:
            raise NoteLibraryError(
                "NOTE_DRAFT_VERSION_CONFLICT", "Draft version has changed"
            )
        await self.session.refresh(draft)
        result = await self.commit(
            note_id,
            RevisionCommit(
                actor_scope=payload.actor_scope,
                expected_base_revision=payload.expected_base_revision,
                expected_draft_version=draft.draft_version,
                idempotency_key=payload.idempotency_key,
            ),
        )
        restored_revision = await self.repository.revision(note_id, result.revision_no)
        assert restored_revision is not None
        restored_revision.origin = "restore"
        restored_revision.restored_from_revision = payload.revision_no
        return await self._revision_read(restored_revision)

    async def patch_metadata(self, note_id: int, payload: MetadataPatch) -> NoteRead:
        await self._require_note(note_id, payload.actor_scope)
        if payload.research_context_ids is not None:
            existing = set(
                await self.session.scalars(
                    select(ResearchContext.id).where(
                        ResearchContext.id.in_(payload.research_context_ids)
                    )
                )
            )
            if existing != set(payload.research_context_ids):
                raise NotFoundError("Research context not found")
        values: dict[str, object] = {}
        if payload.is_favorite is not None:
            values["is_favorite"] = payload.is_favorite
        if not await self.repository.cas_metadata(
            note_id, payload.actor_scope, payload.expected_metadata_version, values
        ):
            raise NoteLibraryError(
                "NOTE_METADATA_VERSION_CONFLICT", "Metadata version has changed"
            )
        if payload.tags is not None:
            await self.repository.replace_tags(note_id, payload.tags)
        if payload.research_context_ids is not None:
            await self.repository.replace_research(
                note_id, payload.research_context_ids
            )
        self.session.add(
            self._activity(note_id, payload.actor_scope, "metadata_updated")
        )
        await self.session.flush()
        return await self.read(note_id, payload.actor_scope)

    async def archive(
        self, note_id: int, actor_scope: str, is_archived: bool
    ) -> NoteRead:
        note = await self._require_note(note_id, actor_scope)
        if note.is_archived != is_archived:
            note.is_archived = is_archived
            note.metadata_version += 1
            self.session.add(
                self._activity(
                    note_id, actor_scope, "archived" if is_archived else "unarchived"
                )
            )
        return await self.read(note_id, actor_scope)

    async def list_notes(
        self,
        actor_scope: str,
        *,
        query: str = "",
        tags: list[str] | None = None,
        research_context_ids: list[int] | None = None,
        favorite: bool | None = None,
        archived: bool = False,
        view: str = "all",
        page: int = 1,
        page_size: int = 20,
    ) -> NoteListRead:
        if page < 1 or page_size not in {20, 50, 100}:
            raise NoteLibraryError(
                "NOTE_QUERY_INVALID", "Invalid page or page_size", status_code=422
            )
        if view not in {"all", "recent", "favorite", "unlinked_research", "archived"}:
            raise NoteLibraryError(
                "NOTE_QUERY_INVALID", "Invalid list view", status_code=422
            )
        if view == "favorite":
            favorite = True
        if view == "archived":
            archived = True
        terms = [term.casefold() for term in query.split() if term]
        window, total = await self.repository.current_note_page(
            actor_scope=actor_scope,
            archived=archived,
            favorite=favorite,
            recent_since=(datetime.now(UTC).replace(tzinfo=None) - timedelta(days=30))
            if view == "recent"
            else None,
            unlinked_only=view == "unlinked_research",
            query_terms=terms,
            tags=tags or [],
            research_context_ids=research_context_ids or [],
            page=page,
            page_size=page_size,
        )
        note_ids = [note.id for note, _ in window]
        revision_ids = [revision.id for _, revision in window]
        tags_by_note: dict[int, list[str]] = defaultdict(list)
        for note_id, tag in await self.repository.tags_for_notes(note_ids):
            tags_by_note[note_id].append(tag.display_name)
        contexts_by_note: dict[int, list[ResearchContext]] = defaultdict(list)
        for note_id, context in await self.repository.research_for_notes(note_ids):
            contexts_by_note[note_id].append(context)
        sources_by_revision = await self._source_reads_for_revisions(revision_ids)
        items = [
            NoteListItem(
                id=note.id,
                current_revision=note.current_revision,
                metadata_version=note.metadata_version,
                title=revision.title,
                excerpt=safe_markdown(revision.body)[:280],
                is_favorite=note.is_favorite,
                is_archived=note.is_archived,
                tags=tags_by_note[note.id],
                research_context_ids=[item.id for item in contexts_by_note[note.id]],
                source_count=len(sources),
                source_summaries=[
                    SourceSummary(
                        source_type=source.source_type,
                        source_id=source.source_id,
                        title=source.title,
                        status=source.status,
                    )
                    for source in sources
                ],
                research_context_summaries=[
                    ResearchContextSummary(id=item.id, name=item.name)
                    for item in contexts_by_note[note.id]
                ],
                content_updated_at=note.content_updated_at,
            )
            for note, revision in window
            for sources in [sources_by_revision[revision.id]]
        ]
        fingerprint = self._fingerprint(
            {
                "q": query,
                "tags": sorted(tags or []),
                "contexts": sorted(research_context_ids or []),
                "favorite": favorite,
                "archived": archived,
                "view": view,
                "page_size": page_size,
            }
        )
        all_total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(ResearchNote)
                .where(
                    ResearchNote.owner_scope == actor_scope,
                    ResearchNote.is_archived.is_(False),
                )
            )
            or 0
        )
        return NoteListRead(
            items=items,
            total=total,
            all_total=all_total,
            page=page,
            page_size=page_size,
            query_fingerprint=fingerprint,
            as_of=datetime.now(UTC),
        )

    async def facets(
        self,
        actor_scope: str,
        *,
        query: str = "",
        tags: list[str] | None = None,
        research_context_ids: list[int] | None = None,
    ) -> FacetsRead:
        tag_entities = list(
            await self.session.scalars(
                select(NoteTag).order_by(NoteTag.normalized_name)
            )
        )
        context_entities = list(
            await self.session.scalars(
                select(ResearchContext).order_by(ResearchContext.id)
            )
        )
        tag_facets = []
        for tag in tag_entities:
            result = await self.list_notes(
                actor_scope,
                query=query,
                tags=[tag.display_name],
                research_context_ids=research_context_ids,
                page_size=100,
            )
            tag_facets.append(
                FacetValue(id=tag.id, name=tag.display_name, count=result.total)
            )
        context_facets = []
        for context in context_entities:
            result = await self.list_notes(
                actor_scope,
                query=query,
                tags=tags,
                research_context_ids=[context.id],
                page_size=100,
            )
            context_facets.append(
                FacetValue(id=context.id, name=context.name, count=result.total)
            )
        active = int(
            await self.session.scalar(
                select(func.count())
                .select_from(ResearchNote)
                .where(
                    ResearchNote.owner_scope == actor_scope,
                    ResearchNote.is_archived.is_(False),
                )
            )
            or 0
        )
        favorite = int(
            await self.session.scalar(
                select(func.count())
                .select_from(ResearchNote)
                .where(
                    ResearchNote.owner_scope == actor_scope,
                    ResearchNote.is_archived.is_(False),
                    ResearchNote.is_favorite.is_(True),
                )
            )
            or 0
        )
        unlinked = int(
            await self.session.scalar(
                select(func.count())
                .select_from(ResearchNote)
                .where(
                    ResearchNote.owner_scope == actor_scope,
                    ResearchNote.is_archived.is_(False),
                    ~ResearchNote.id.in_(select(NoteResearchLink.note_id)),
                )
            )
            or 0
        )
        fingerprint = self._fingerprint(
            {
                "q": query,
                "tags": sorted(tags or []),
                "contexts": sorted(research_context_ids or []),
            }
        )
        return FacetsRead(
            tags=tag_facets,
            research_contexts=context_facets,
            quick_counts={
                "all": active,
                "favorite": favorite,
                "unlinked_research": unlinked,
                "recent": int(
                    await self.session.scalar(
                        select(func.count())
                        .select_from(ResearchNote)
                        .where(
                            ResearchNote.owner_scope == actor_scope,
                            ResearchNote.is_archived.is_(False),
                            ResearchNote.content_updated_at
                            >= datetime.now(UTC).replace(tzinfo=None)
                            - timedelta(days=30),
                        )
                    )
                    or 0
                ),
            },
            query_fingerprint=fingerprint,
            as_of=datetime.now(UTC),
        )

    async def create_suggestion(
        self, note_id: int, payload: AISuggestionCreate
    ) -> AISuggestionRead:
        await self._require_note(note_id, payload.actor_scope)
        if not payload.cloud_consent:
            raise NoteLibraryError(
                "CLOUD_CONSENT_REQUIRED",
                "Cloud processing consent is required",
                status_code=403,
            )
        draft = await self.repository.draft(note_id, payload.actor_scope)
        suggestion = NoteAISuggestion(
            note_id=note_id,
            input_revision=payload.input_revision,
            input_draft_version=payload.input_draft_version,
            operation=payload.operation,
        )
        self.session.add(suggestion)
        await self.session.flush()
        await self.ai_provider.enqueue(suggestion.id, (draft.body if draft else ""))
        return self._suggestion_read(suggestion)

    async def suggestion(
        self, suggestion_id: int, actor_scope: str
    ) -> AISuggestionRead:
        suggestion = await self.session.get(NoteAISuggestion, suggestion_id)
        if suggestion is None:
            raise NotFoundError("AI suggestion not found")
        await self._require_note(suggestion.note_id, actor_scope)
        return self._suggestion_read(suggestion)

    async def start_suggestion(self, suggestion_id: int) -> AISuggestionRead:
        """Move a fake/provider task to running without changing note content."""
        suggestion = await self.session.get(NoteAISuggestion, suggestion_id)
        if suggestion is None:
            raise NotFoundError("AI suggestion not found")
        if suggestion.status == "queued":
            suggestion.status = "running"
        return self._suggestion_read(suggestion)

    async def complete_suggestion(
        self, suggestion_id: int, payload: AISuggestionComplete
    ) -> AISuggestionRead:
        suggestion = await self.session.get(NoteAISuggestion, suggestion_id)
        if suggestion is None:
            raise NotFoundError("AI suggestion not found")
        if suggestion.status == "cancelled":
            return self._suggestion_read(suggestion)
        suggestion.status = "failed" if payload.failed else "succeeded"
        suggestion.output_title, suggestion.output_body = payload.title, payload.body
        note = await self.session.get(ResearchNote, suggestion.note_id)
        draft = await self.session.scalar(
            select(NoteDraft).where(NoteDraft.note_id == suggestion.note_id)
        )
        suggestion.is_stale = bool(
            (
                suggestion.input_revision is not None
                and note
                and note.current_revision != suggestion.input_revision
            )
            or (
                suggestion.input_draft_version is not None
                and draft
                and draft.draft_version != suggestion.input_draft_version
            )
        )
        return self._suggestion_read(suggestion)

    async def timeout_suggestion(self, suggestion_id: int) -> AISuggestionRead:
        """Record a bounded provider timeout while preserving the user's draft."""
        suggestion = await self.session.get(NoteAISuggestion, suggestion_id)
        if suggestion is None:
            raise NotFoundError("AI suggestion not found")
        if suggestion.status in {"queued", "running"}:
            suggestion.status = "failed"
        return self._suggestion_read(suggestion)

    async def cancel_suggestion(
        self, suggestion_id: int, actor_scope: str
    ) -> AISuggestionRead:
        suggestion = await self.session.get(NoteAISuggestion, suggestion_id)
        if suggestion is None:
            raise NotFoundError("AI suggestion not found")
        await self._require_note(suggestion.note_id, actor_scope)
        if suggestion.status in {"queued", "running"}:
            suggestion.status = "cancelled"
        return self._suggestion_read(suggestion)

    async def adopt_suggestion(
        self, suggestion_id: int, payload: AISuggestionAdopt
    ) -> DraftRead:
        suggestion = await self.session.get(NoteAISuggestion, suggestion_id)
        if suggestion is None:
            raise NotFoundError("AI suggestion not found")
        draft = await self.repository.draft(suggestion.note_id, payload.actor_scope)
        if draft is None:
            raise NotFoundError("Note draft not found")
        if (
            suggestion.status != "succeeded"
            or suggestion.is_stale
            or draft.draft_version != payload.expected_draft_version
        ):
            raise NoteLibraryError(
                "NOTE_DRAFT_VERSION_CONFLICT", "Suggestion input is stale"
            )
        draft.title = (
            suggestion.output_title
            if suggestion.output_title is not None
            else draft.title
        )
        draft.body = (
            suggestion.output_body if suggestion.output_body is not None else draft.body
        )
        draft.draft_version += 1
        suggestion.adopted_at = datetime.now(UTC)
        return self._draft_read(draft)

    async def derive(self, note_id: int, payload: DerivationCreate) -> DerivationRead:
        await self._require_note(note_id, payload.actor_scope)
        revision = await self.repository.revision(note_id, payload.revision_no)
        if revision is None:
            raise NotFoundError("Note revision not found")
        previous = await self.session.scalar(
            select(NoteDerivation).where(
                NoteDerivation.actor_scope == payload.actor_scope,
                NoteDerivation.idempotency_key == payload.idempotency_key,
            )
        )
        if previous is not None:
            if (
                previous.note_id != note_id
                or previous.revision_id != revision.id
                or previous.target_type != payload.target_type
            ):
                raise NoteLibraryError(
                    "IDEMPOTENCY_KEY_REUSED", "Idempotency key was reused"
                )
            return self._derivation_read(previous)
        if payload.target_type in {"claim", "evidence"}:
            raise NoteLibraryError(
                "TARGET_CAPABILITY_UNAVAILABLE", "Target capability is unavailable"
            )
        entity = NoteDerivation(
            actor_scope=payload.actor_scope,
            note_id=note_id,
            revision_id=revision.id,
            target_type=payload.target_type,
            idempotency_key=payload.idempotency_key,
        )
        self.session.add(entity)
        await self.session.flush()
        return self._derivation_read(entity)

    async def export(self, payload: ExportRequest) -> ExportRead:
        note = await self._require_note(payload.note_id, payload.actor_scope)
        revision_no = payload.revision_no or note.current_revision
        revision = await self.repository.revision(note.id, revision_no)
        if revision is None:
            raise NotFoundError("Note revision not found")
        sources = await self._source_reads(revision.id)
        if payload.format == "json":
            content = json.dumps(
                {
                    "note_id": note.id,
                    "revision_no": revision.revision_no,
                    "title": revision.title,
                    "body": safe_markdown(revision.body),
                    "sources": [item.model_dump(mode="json") for item in sources],
                },
                ensure_ascii=False,
                indent=2,
            )
            return ExportRead(
                filename=safe_filename(revision.title, "json"),
                media_type="application/json",
                content=content,
                revision_no=revision.revision_no,
            )
        source_lines = [f"- {item.title} ({item.status})" for item in sources]
        content = (
            f"# {safe_markdown(revision.title)}\n\n{safe_markdown(revision.body)}\n\n## Sources\n"
            + ("\n".join(source_lines) or "- None")
        )
        return ExportRead(
            filename=safe_filename(revision.title, "md"),
            media_type="text/markdown",
            content=content,
            revision_no=revision.revision_no,
        )

    async def backfill_legacy(
        self, actor_scope: str, *, dry_run: bool
    ) -> LegacyBackfillRead:
        legacy = list(
            await self.session.scalars(
                select(DocumentReadingNote).order_by(DocumentReadingNote.id)
            )
        )
        existing = set(await self.session.scalars(select(NoteLegacyBackfill.legacy_id)))
        eligible = len(legacy)
        pending = [item for item in legacy if item.id not in existing]
        if dry_run:
            return LegacyBackfillRead(
                dry_run=True,
                eligible=eligible,
                created=0,
                skipped=eligible - len(pending),
            )
        for item in pending:
            note = ResearchNote(owner_scope=actor_scope, current_revision=1)
            self.session.add(note)
            await self.session.flush()
            revision = NoteRevision(
                note_id=note.id,
                revision_no=1,
                title=f"Legacy reading note {item.id}",
                body=item.content,
                origin="legacy_backfill",
            )
            draft = NoteDraft(
                note_id=note.id,
                actor_scope=actor_scope,
                base_revision=1,
                title=revision.title,
                body=revision.body,
            )
            self.session.add_all([revision, draft])
            await self.session.flush()
            self.session.add_all(
                [
                    NoteSourceLink(
                        revision_id=revision.id,
                        source_type="anchor",
                        source_id=item.source_anchor_id,
                        document_id=item.document_id,
                        anchor_id=item.source_anchor_id,
                        granularity="exact_anchor",
                        quote_snapshot=item.quote_snapshot,
                        created_status="accessible",
                    ),
                    NoteLegacyBackfill(
                        legacy_id=item.id,
                        note_id=note.id,
                        document_id=item.document_id,
                        anchor_id=item.source_anchor_id,
                        quote_snapshot=item.quote_snapshot,
                    ),
                ]
            )
        await self.session.flush()
        return LegacyBackfillRead(
            dry_run=False,
            eligible=eligible,
            created=len(pending),
            skipped=eligible - len(pending),
        )

    async def _require_note(self, note_id: int, actor_scope: str) -> ResearchNote:
        note = await self.repository.note(note_id, actor_scope)
        if note is None:
            raise NotFoundError("Note not found")
        return note

    async def _freeze_sources(
        self, revision_id: int, sources: list[SourceInput]
    ) -> None:
        for source in sources:
            if source.source_type == "anchor":
                anchor = await self.session.get(DocumentSourceAnchor, source.anchor_id)
                if anchor is None:
                    raise NoteLibraryError(
                        "SOURCE_UNAVAILABLE", "Anchor source is unavailable"
                    )
                revision = await self.session.get(
                    DocumentAnchorRevision, anchor.anchor_revision_id
                )
                assert revision is not None
                if source.quote is not None and source.quote != anchor.quote:
                    raise NoteLibraryError(
                        "SOURCE_QUOTE_MISMATCH",
                        "Client quote does not match the fixed anchor",
                    )
                document = await self.session.get(Document, revision.document_id)
                if document is None:
                    raise NoteLibraryError(
                        "SOURCE_UNAVAILABLE", "Anchor document is unavailable"
                    )
                knowledge_source = await self.session.get(
                    KnowledgeSource, document.knowledge_source_id
                )
                if knowledge_source is None or not knowledge_source.enabled:
                    raise NoteLibraryError(
                        "SOURCE_ACCESS_DENIED",
                        "Anchor source is not accessible",
                        status_code=403,
                    )
                self.session.add(
                    NoteSourceLink(
                        revision_id=revision_id,
                        source_type="anchor",
                        source_id=anchor.id,
                        source_version=revision.file_hash,
                        document_id=revision.document_id,
                        anchor_id=anchor.id,
                        granularity="exact_anchor",
                        title_snapshot=document.parsed_title
                        or document.file_path.rsplit("/", 1)[-1],
                        quote_snapshot=anchor.quote,
                        url_snapshot=safe_url(source.url),
                        created_status="accessible",
                    )
                )
                continue
            if source.source_type == "document":
                document_id = source.source_id or source.document_id
                document = await self.session.get(Document, document_id)
                if document is None or source.document_id not in {None, document.id}:
                    raise NoteLibraryError(
                        "SOURCE_UNAVAILABLE", "Document source is unavailable"
                    )
                knowledge_source = await self.session.get(
                    KnowledgeSource, document.knowledge_source_id
                )
                if knowledge_source is None or not knowledge_source.enabled:
                    raise NoteLibraryError(
                        "SOURCE_ACCESS_DENIED",
                        "Document source is not accessible",
                        status_code=403,
                    )
                self.session.add(
                    NoteSourceLink(
                        revision_id=revision_id,
                        source_type="document",
                        source_id=document.id,
                        source_version=document.file_hash,
                        document_id=document.id,
                        granularity="bibliographic",
                        title_snapshot=document.parsed_title
                        or document.file_path.rsplit("/", 1)[-1],
                        url_snapshot=None,
                        created_status="accessible",
                    )
                )
                continue
            if source.source_type == "paper":
                paper = (
                    await self.session.get(LibraryItem, source.source_id)
                    if source.source_id is not None
                    else await self.session.scalar(
                        select(LibraryItem).where(
                            LibraryItem.document_id == source.document_id
                        )
                    )
                )
                if paper is None or (
                    source.document_id is not None
                    and paper.document_id != source.document_id
                ):
                    raise NoteLibraryError(
                        "SOURCE_UNAVAILABLE", "Paper source is unavailable"
                    )
                if paper.document_id is not None:
                    document = await self.session.get(Document, paper.document_id)
                    knowledge_source = (
                        await self.session.get(
                            KnowledgeSource, document.knowledge_source_id
                        )
                        if document
                        else None
                    )
                    if (
                        document is None
                        or knowledge_source is None
                        or not knowledge_source.enabled
                    ):
                        raise NoteLibraryError(
                            "SOURCE_ACCESS_DENIED",
                            "Paper source is not accessible",
                            status_code=403,
                        )
                self.session.add(
                    NoteSourceLink(
                        revision_id=revision_id,
                        source_type="paper",
                        source_id=paper.id,
                        source_version=paper.doi or paper.pmid,
                        document_id=paper.document_id,
                        granularity="bibliographic",
                        title_snapshot=paper.title or f"Paper {paper.id}",
                        url_snapshot=None,
                        created_status="accessible",
                    )
                )
                continue
            self.session.add(
                NoteSourceLink(
                    revision_id=revision_id,
                    source_type=source.source_type,
                    source_id=source.source_id,
                    source_version=source.source_version,
                    document_id=source.document_id,
                    granularity="bibliographic",
                    title_snapshot=source.title,
                    url_snapshot=safe_url(source.url),
                    created_status="accessible",
                )
            )

    async def _source_reads(self, revision_id: int) -> list[SourceRead]:
        return [
            await self._source_read(item)
            for item in await self.repository.sources(revision_id)
        ]

    async def _source_reads_for_revisions(
        self, revision_ids: list[int]
    ) -> dict[int, list[SourceRead]]:
        links = await self.repository.sources_for_revisions(revision_ids)
        document_ids = list({item.document_id for item in links if item.document_id})
        documents = (
            {
                item.id: item
                for item in await self.session.scalars(
                    select(Document).where(Document.id.in_(document_ids))
                )
            }
            if document_ids
            else {}
        )
        source_ids = list({item.knowledge_source_id for item in documents.values()})
        knowledge_sources = (
            {
                item.id: item
                for item in await self.session.scalars(
                    select(KnowledgeSource).where(KnowledgeSource.id.in_(source_ids))
                )
            }
            if source_ids
            else {}
        )
        result: dict[int, list[SourceRead]] = defaultdict(list)
        for item in links:
            status = item.created_status
            title = item.title_snapshot
            document_id = item.document_id
            document = documents.get(document_id) if document_id is not None else None
            if document_id is not None and (
                document is None
                or not knowledge_sources.get(document.knowledge_source_id, None)
                or not knowledge_sources[document.knowledge_source_id].enabled
            ):
                status, title = "access_revoked", "Restricted source"
            elif (
                document is not None
                and item.source_version
                and document.file_hash != item.source_version
            ):
                status = "review_required"
            result[item.revision_id].append(
                SourceRead(
                    id=item.id,
                    source_type=item.source_type,
                    source_id=item.source_id,
                    document_id=item.document_id,
                    anchor_id=item.anchor_id,
                    granularity=item.granularity,
                    status=status,
                    title=title,
                    quote=None,
                    url=safe_url(item.url_snapshot)
                    if status != "access_revoked"
                    else None,
                    capabilities=[],
                )
            )
        return result

    async def _source_read(self, item: NoteSourceLink) -> SourceRead:
        status = item.created_status
        quote: str | None = item.quote_snapshot or None
        capabilities: list[str] = []
        if item.document_id is not None:
            document = await self.session.get(Document, item.document_id)
            source = (
                await self.session.get(KnowledgeSource, document.knowledge_source_id)
                if document
                else None
            )
            if document is None or source is None or not source.enabled:
                status, quote = "access_revoked", None
            elif item.source_version and document.file_hash != item.source_version:
                status = "review_required"
            elif item.anchor_id is not None:
                anchor = await self.session.get(DocumentSourceAnchor, item.anchor_id)
                if anchor is not None and anchor.resolution_status == "exact":
                    capabilities.append("view_source_location")
        return SourceRead(
            id=item.id,
            source_type=item.source_type,
            source_id=item.source_id,
            document_id=item.document_id,
            anchor_id=item.anchor_id,
            granularity=item.granularity,
            status=status,
            title=item.title_snapshot
            if status != "access_revoked"
            else "Restricted source",
            quote=quote,
            url=safe_url(item.url_snapshot) if status != "access_revoked" else None,
            capabilities=capabilities,
        )

    async def _research_contexts(self, context_ids: list[int]) -> list[ResearchContext]:
        if not context_ids:
            return []
        return list(
            await self.session.scalars(
                select(ResearchContext)
                .where(ResearchContext.id.in_(context_ids))
                .order_by(ResearchContext.id)
            )
        )

    async def _revision_read(self, revision: NoteRevision) -> RevisionRead:
        return RevisionRead(
            id=revision.id,
            note_id=revision.note_id,
            revision_no=revision.revision_no,
            title=revision.title,
            body=safe_markdown(revision.body),
            origin=revision.origin,
            restored_from_revision=revision.restored_from_revision,
            sources=await self._source_reads(revision.id),
            created_at=revision.created_at,
        )

    @staticmethod
    def _draft_read(draft: NoteDraft) -> DraftRead:
        return DraftRead(
            note_id=draft.note_id,
            actor_scope=draft.actor_scope,
            base_revision=draft.base_revision,
            draft_version=draft.draft_version,
            title=draft.title,
            body=draft.body,
            sources=NoteLibraryService._parse_sources(draft.sources_json),
            save_state=draft.save_state,
            updated_at=draft.updated_at,
        )

    @staticmethod
    def _sources_json(sources: list[SourceInput]) -> str:
        return json.dumps(
            [item.model_dump(mode="json") for item in sources], sort_keys=True
        )

    @staticmethod
    def _parse_sources(value: str) -> list[SourceInput]:
        return [SourceInput.model_validate(item) for item in json.loads(value)]

    @staticmethod
    def _source_input(item: NoteSourceLink) -> SourceInput:
        return SourceInput.model_validate(
            {
                "source_type": item.source_type,
                "source_id": item.source_id,
                "source_version": item.source_version,
                "document_id": item.document_id,
                "anchor_id": item.anchor_id,
                "quote": item.quote_snapshot or None,
                "title": item.title_snapshot,
                "url": item.url_snapshot,
            }
        )

    @staticmethod
    def _request_hash(payload: RevisionCommit, draft: NoteDraft) -> str:
        value = json.dumps(
            {
                "base": payload.expected_base_revision,
                "draft": payload.expected_draft_version,
                "title": draft.title,
                "body": draft.body,
                "sources": json.loads(draft.sources_json),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
        return hashlib.sha256(value.encode()).hexdigest()

    @staticmethod
    def _fingerprint(value: object) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()

    @staticmethod
    def _timestamp(value: datetime) -> float:
        return (
            value.replace(tzinfo=UTC).timestamp()
            if value.tzinfo is None
            else value.timestamp()
        )

    @staticmethod
    def _activity(
        note_id: int,
        actor_scope: str,
        action: str,
        detail: dict[str, object] | None = None,
    ) -> NoteActivity:
        return NoteActivity(
            note_id=note_id,
            actor_scope=actor_scope,
            action=action,
            detail_json=json.dumps(detail or {}, sort_keys=True),
        )

    @staticmethod
    def _suggestion_read(item: NoteAISuggestion) -> AISuggestionRead:
        return AISuggestionRead(
            id=item.id,
            note_id=item.note_id,
            input_revision=item.input_revision,
            input_draft_version=item.input_draft_version,
            operation=item.operation,
            status=item.status,
            title=item.output_title,
            body=item.output_body,
            is_stale=item.is_stale,
            adopted_at=item.adopted_at,
        )

    @staticmethod
    def _derivation_read(item: NoteDerivation) -> DerivationRead:
        return DerivationRead(
            id=item.id,
            note_id=item.note_id,
            revision_id=item.revision_id,
            target_type=item.target_type,
            status=item.status,
        )
