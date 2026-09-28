"""Bounded source projections for the paper-research center."""

from datetime import datetime
from typing import cast

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.document.model import Document
from app.modules.document_reader.model import ReaderSession
from app.modules.library_item.model import LibraryItem
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_library.model import (
    PaperActivity,
    PaperLibraryMember,
    PaperResearchCenterPreference,
    PaperResearchRelation,
    PaperWorkState,
)
from app.modules.research_context.model import ResearchContext


class CenterRepository:
    """Keep center reads set-based; no per-paper ORM relationship loads."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def preference(self, actor_scope: str):
        result = await self.session.execute(
            select(PaperResearchCenterPreference, ResearchContext.name)
            .outerjoin(
                ResearchContext,
                ResearchContext.id == PaperResearchCenterPreference.research_context_id,
            )
            .where(PaperResearchCenterPreference.actor_scope == actor_scope)
        )
        return result.first()

    async def context_exists(self, context_id: int) -> bool:
        return (
            await self.session.scalar(
                select(ResearchContext.id).where(ResearchContext.id == context_id)
            )
            is not None
        )

    async def create_preference(
        self, actor_scope: str, context_id: int | None, stage: str
    ) -> PaperResearchCenterPreference:
        preference = PaperResearchCenterPreference(
            actor_scope=actor_scope,
            research_context_id=context_id,
            stage=stage,
            version=1,
        )
        self.session.add(preference)
        await self.session.flush()
        return preference

    async def update_preference(
        self,
        preference: PaperResearchCenterPreference,
        expected_version: int,
        *,
        context_id: int | None = None,
        stage: str | None = None,
        replace_context: bool = False,
    ) -> bool:
        values: dict[str, object] = {"version": expected_version + 1}
        if replace_context:
            values["research_context_id"] = context_id
        if stage is not None:
            values["stage"] = stage
        result = await self.session.execute(
            update(PaperResearchCenterPreference)
            .where(
                and_(
                    PaperResearchCenterPreference.id == preference.id,
                    PaperResearchCenterPreference.version == expected_version,
                )
            )
            .values(**values)
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def work_rows(self, context_id: int | None, actor_scope: str):
        latest_analysis = aliased(PaperAnalysis)
        latest_analysis_id = (
            select(latest_analysis.id)
            .where(latest_analysis.document_id == LibraryItem.document_id)
            .order_by(latest_analysis.updated_at.desc(), latest_analysis.id.desc())
            .limit(1)
            .correlate(LibraryItem)
            .scalar_subquery()
        )
        latest_reader = aliased(ReaderSession)
        latest_reader_id = (
            select(latest_reader.id)
            .where(
                latest_reader.library_item_id == LibraryItem.id,
                latest_reader.actor_scope == actor_scope,
                latest_reader.is_history_hidden.is_(False),
                latest_reader.document_file_hash == Document.file_hash,
            )
            .order_by(latest_reader.last_seen_at.desc(), latest_reader.id.desc())
            .limit(1)
            .correlate(LibraryItem, Document)
            .scalar_subquery()
        )
        statement = (
            select(LibraryItem, PaperWorkState, PaperAnalysis, ReaderSession)
            .join(
                PaperLibraryMember, PaperLibraryMember.library_item_id == LibraryItem.id
            )
            .outerjoin(PaperWorkState, PaperWorkState.library_item_id == LibraryItem.id)
            .outerjoin(Document, Document.id == LibraryItem.document_id)
            .outerjoin(PaperAnalysis, PaperAnalysis.id == latest_analysis_id)
            .outerjoin(
                ReaderSession,
                ReaderSession.id == latest_reader_id,
            )
        )
        if context_id is not None:
            statement = statement.join(
                PaperResearchRelation,
                PaperResearchRelation.library_item_id == LibraryItem.id,
            ).where(PaperResearchRelation.research_context_id == context_id)
        result = await self.session.execute(statement.order_by(LibraryItem.id))
        return list(result.all())

    async def activities(
        self, actor_scope: str, cursor: tuple[datetime, int] | None, limit: int
    ):
        statement = (
            select(
                PaperActivity, LibraryItem, PaperResearchRelation, ResearchContext.name
            )
            .join(LibraryItem, LibraryItem.id == PaperActivity.library_item_id)
            .outerjoin(
                PaperResearchRelation,
                PaperResearchRelation.library_item_id == LibraryItem.id,
            )
            .outerjoin(
                ResearchContext,
                ResearchContext.id == PaperResearchRelation.research_context_id,
            )
            .where(PaperActivity.actor_scope == actor_scope)
        )
        if cursor:
            statement = statement.where(
                or_(
                    PaperActivity.created_at < cursor[0],
                    and_(
                        PaperActivity.created_at == cursor[0],
                        PaperActivity.id < cursor[1],
                    ),
                )
            )
        result = await self.session.execute(
            statement.order_by(
                PaperActivity.created_at.desc(), PaperActivity.id.desc()
            ).limit(limit)
        )
        return list(result.all())

    async def summary(self):
        latest_analysis = aliased(PaperAnalysis)
        latest_analysis_id = (
            select(latest_analysis.id)
            .where(latest_analysis.document_id == LibraryItem.document_id)
            .order_by(latest_analysis.updated_at.desc(), latest_analysis.id.desc())
            .limit(1)
            .correlate(LibraryItem)
            .scalar_subquery()
        )
        pending = func.coalesce(PaperAnalysis.pending_confirmations, "[]")
        row = (
            await self.session.execute(
                select(
                    func.count(func.distinct(LibraryItem.id)),
                    func.count(func.distinct(LibraryItem.id)).filter(
                        PaperWorkState.reading_status == "reading"
                    ),
                    func.count(func.distinct(LibraryItem.id)).filter(
                        PaperAnalysis.analysis_status.in_(("pending", "analyzing"))
                    ),
                    func.count(func.distinct(LibraryItem.id)).filter(
                        and_(
                            PaperWorkState.reading_status == "read",
                            or_(
                                PaperAnalysis.id.is_(None),
                                ~PaperAnalysis.analysis_status.in_(
                                    ("pending", "analyzing")
                                ),
                            ),
                        )
                    ),
                    func.count(func.distinct(LibraryItem.id)).filter(pending != "[]"),
                )
                .select_from(LibraryItem)
                .join(PaperLibraryMember)
                .outerjoin(PaperWorkState)
                .outerjoin(PaperAnalysis, PaperAnalysis.id == latest_analysis_id)
            )
        ).one()
        # JSON array length is dialect-sensitive, so fields are counted from bounded analysis strings in the projector.
        return row

    async def pending_confirmation_values(self) -> list[str | None]:
        """Read only latest JSON fields; parsing remains dialect-neutral in projector."""
        latest_analysis = aliased(PaperAnalysis)
        latest_analysis_id = (
            select(latest_analysis.id)
            .where(latest_analysis.document_id == LibraryItem.document_id)
            .order_by(latest_analysis.updated_at.desc(), latest_analysis.id.desc())
            .limit(1)
            .correlate(LibraryItem)
            .scalar_subquery()
        )
        result = await self.session.execute(
            select(PaperAnalysis.pending_confirmations)
            .select_from(LibraryItem)
            .join(PaperLibraryMember)
            .outerjoin(PaperAnalysis, PaperAnalysis.id == latest_analysis_id)
        )
        return list(result.scalars())
