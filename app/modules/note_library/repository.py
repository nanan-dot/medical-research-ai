"""Database access for the note-library aggregate."""

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document.model import Document
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.note_library.model import (
    NoteDraft,
    NoteResearchLink,
    NoteRevision,
    NoteSourceLink,
    NoteTag,
    NoteTagLink,
    ResearchNote,
)
from app.modules.research_context.model import ResearchContext


class NoteLibraryRepository:
    """Keep SQL construction below the domain service boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def note(self, note_id: int, owner_scope: str) -> ResearchNote | None:
        return await self.session.scalar(
            select(ResearchNote).where(
                ResearchNote.id == note_id, ResearchNote.owner_scope == owner_scope
            )
        )

    async def draft(self, note_id: int, actor_scope: str) -> NoteDraft | None:
        return await self.session.scalar(
            select(NoteDraft).where(
                NoteDraft.note_id == note_id, NoteDraft.actor_scope == actor_scope
            )
        )

    async def revision(self, note_id: int, revision_no: int) -> NoteRevision | None:
        return await self.session.scalar(
            select(NoteRevision).where(
                NoteRevision.note_id == note_id,
                NoteRevision.revision_no == revision_no,
            )
        )

    async def revisions(self, note_id: int) -> Sequence[NoteRevision]:
        result = await self.session.scalars(
            select(NoteRevision)
            .where(NoteRevision.note_id == note_id)
            .order_by(NoteRevision.revision_no.desc())
        )
        return result.all()

    async def revision_page(
        self, note_id: int, *, page: int, page_size: int
    ) -> tuple[Sequence[NoteRevision], int]:
        total = int(
            await self.session.scalar(
                select(func.count())
                .select_from(NoteRevision)
                .where(NoteRevision.note_id == note_id)
            )
            or 0
        )
        result = await self.session.scalars(
            select(NoteRevision)
            .where(NoteRevision.note_id == note_id)
            .order_by(NoteRevision.revision_no.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return result.all(), total

    async def current_note_page(
        self,
        *,
        actor_scope: str,
        archived: bool,
        favorite: bool | None,
        recent_since: datetime | None,
        unlinked_only: bool,
        query_terms: list[str],
        tags: list[str],
        research_context_ids: list[int],
        page: int,
        page_size: int,
    ) -> tuple[Sequence[tuple[ResearchNote, NoteRevision]], int]:
        statement = (
            select(ResearchNote, NoteRevision)
            .join(
                NoteRevision,
                and_(
                    NoteRevision.note_id == ResearchNote.id,
                    NoteRevision.revision_no == ResearchNote.current_revision,
                ),
            )
            .where(
                ResearchNote.owner_scope == actor_scope,
                ResearchNote.is_archived == archived,
            )
        )
        if favorite is not None:
            statement = statement.where(ResearchNote.is_favorite == favorite)
        if recent_since is not None:
            statement = statement.where(ResearchNote.content_updated_at >= recent_since)
        if unlinked_only:
            statement = statement.where(
                ~exists(
                    select(NoteResearchLink.id).where(
                        NoteResearchLink.note_id == ResearchNote.id
                    )
                )
            )
        if tags:
            statement = statement.where(
                exists(
                    select(NoteTagLink.id)
                    .join(NoteTag, NoteTag.id == NoteTagLink.tag_id)
                    .where(
                        NoteTagLink.note_id == ResearchNote.id,
                        func.lower(NoteTag.normalized_name).in_(
                            [item.casefold() for item in tags]
                        ),
                    )
                )
            )
        if research_context_ids:
            statement = statement.where(
                exists(
                    select(NoteResearchLink.id).where(
                        NoteResearchLink.note_id == ResearchNote.id,
                        NoteResearchLink.research_context_id.in_(research_context_ids),
                    )
                )
            )
        for term in query_terms:
            pattern = f"%{term}%"
            statement = statement.where(
                or_(
                    func.lower(NoteRevision.title).like(pattern),
                    func.lower(NoteRevision.body).like(pattern),
                    exists(
                        select(NoteTagLink.id)
                        .join(NoteTag, NoteTag.id == NoteTagLink.tag_id)
                        .where(
                            NoteTagLink.note_id == ResearchNote.id,
                            func.lower(NoteTag.display_name).like(pattern),
                        )
                    ),
                    exists(
                        select(NoteResearchLink.id)
                        .join(
                            ResearchContext,
                            ResearchContext.id == NoteResearchLink.research_context_id,
                        )
                        .where(
                            NoteResearchLink.note_id == ResearchNote.id,
                            func.lower(ResearchContext.name).like(pattern),
                        )
                    ),
                    exists(
                        select(NoteSourceLink.id).where(
                            NoteSourceLink.revision_id == NoteRevision.id,
                            func.lower(NoteSourceLink.title_snapshot).like(pattern),
                            or_(
                                NoteSourceLink.document_id.is_(None),
                                exists(
                                    select(Document.id)
                                    .join(
                                        KnowledgeSource,
                                        KnowledgeSource.id
                                        == Document.knowledge_source_id,
                                    )
                                    .where(
                                        Document.id == NoteSourceLink.document_id,
                                        KnowledgeSource.enabled.is_(True),
                                    )
                                ),
                            ),
                        )
                    ),
                )
            )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(statement.subquery())
            )
            or 0
        )
        result = await self.session.execute(
            statement.order_by(
                ResearchNote.content_updated_at.desc(), ResearchNote.id.desc()
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return cast(
            list[tuple[ResearchNote, NoteRevision]], result.tuples().all()
        ), total

    async def sources(self, revision_id: int) -> Sequence[NoteSourceLink]:
        result = await self.session.scalars(
            select(NoteSourceLink)
            .where(NoteSourceLink.revision_id == revision_id)
            .order_by(NoteSourceLink.id)
        )
        return result.all()

    async def sources_for_revisions(
        self, revision_ids: list[int]
    ) -> Sequence[NoteSourceLink]:
        if not revision_ids:
            return []
        result = await self.session.scalars(
            select(NoteSourceLink)
            .where(NoteSourceLink.revision_id.in_(revision_ids))
            .order_by(NoteSourceLink.revision_id, NoteSourceLink.id)
        )
        return result.all()

    async def tags_for_notes(
        self, note_ids: list[int]
    ) -> Sequence[tuple[int, NoteTag]]:
        if not note_ids:
            return []
        result = await self.session.execute(
            select(NoteTagLink.note_id, NoteTag)
            .join(NoteTag, NoteTag.id == NoteTagLink.tag_id)
            .where(NoteTagLink.note_id.in_(note_ids))
            .order_by(NoteTagLink.note_id, NoteTag.normalized_name)
        )
        return cast(list[tuple[int, NoteTag]], result.tuples().all())

    async def research_for_notes(
        self, note_ids: list[int]
    ) -> Sequence[tuple[int, ResearchContext]]:
        if not note_ids:
            return []
        result = await self.session.execute(
            select(NoteResearchLink.note_id, ResearchContext)
            .join(
                ResearchContext,
                ResearchContext.id == NoteResearchLink.research_context_id,
            )
            .where(NoteResearchLink.note_id.in_(note_ids))
            .order_by(NoteResearchLink.note_id, ResearchContext.id)
        )
        return cast(list[tuple[int, ResearchContext]], result.tuples().all())

    async def tags(self, note_id: int) -> Sequence[NoteTag]:
        result = await self.session.scalars(
            select(NoteTag)
            .join(NoteTagLink, NoteTagLink.tag_id == NoteTag.id)
            .where(NoteTagLink.note_id == note_id)
            .order_by(NoteTag.normalized_name)
        )
        return result.all()

    async def research_ids(self, note_id: int) -> list[int]:
        result = await self.session.scalars(
            select(NoteResearchLink.research_context_id)
            .where(NoteResearchLink.note_id == note_id)
            .order_by(NoteResearchLink.research_context_id)
        )
        return list(result)

    async def replace_tags(self, note_id: int, values: list[str]) -> None:
        await self.session.execute(
            delete(NoteTagLink).where(NoteTagLink.note_id == note_id)
        )
        for display_name in dict.fromkeys(values):
            normalized = display_name.casefold().strip()
            tag = await self.session.scalar(
                select(NoteTag).where(NoteTag.normalized_name == normalized)
            )
            if tag is None:
                tag = NoteTag(
                    normalized_name=normalized, display_name=display_name.strip()
                )
                self.session.add(tag)
                await self.session.flush()
            self.session.add(NoteTagLink(note_id=note_id, tag_id=tag.id))

    async def replace_research(self, note_id: int, context_ids: list[int]) -> None:
        await self.session.execute(
            delete(NoteResearchLink).where(NoteResearchLink.note_id == note_id)
        )
        self.session.add_all(
            [
                NoteResearchLink(note_id=note_id, research_context_id=value)
                for value in dict.fromkeys(context_ids)
            ]
        )

    async def cas_draft(
        self,
        draft_id: int,
        expected_version: int,
        *,
        title: str,
        body: str,
        sources_json: str,
        base_revision: int | None = None,
    ) -> bool:
        values: dict[str, object] = {
            "title": title,
            "body": body,
            "sources_json": sources_json,
            "draft_version": expected_version + 1,
            "save_state": "draft_saved",
        }
        if base_revision is not None:
            values["base_revision"] = base_revision
        result = await self.session.execute(
            update(NoteDraft)
            .where(
                NoteDraft.id == draft_id, NoteDraft.draft_version == expected_version
            )
            .values(**values)
        )
        return getattr(result, "rowcount", 0) == 1

    async def cas_note_revision(
        self, note_id: int, owner_scope: str, expected_revision: int
    ) -> bool:
        result = await self.session.execute(
            update(ResearchNote)
            .where(
                ResearchNote.id == note_id,
                ResearchNote.owner_scope == owner_scope,
                ResearchNote.current_revision == expected_revision,
            )
            .values(
                current_revision=expected_revision + 1,
                content_updated_at=func.current_timestamp(),
            )
        )
        return getattr(result, "rowcount", 0) == 1

    async def cas_metadata(
        self, note_id: int, owner_scope: str, expected: int, values: dict[str, object]
    ) -> bool:
        result = await self.session.execute(
            update(ResearchNote)
            .where(
                ResearchNote.id == note_id,
                ResearchNote.owner_scope == owner_scope,
                ResearchNote.metadata_version == expected,
            )
            .values(**values, metadata_version=expected + 1)
        )
        return getattr(result, "rowcount", 0) == 1
