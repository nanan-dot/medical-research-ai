"""论文库有界查询与持久化访问。"""

from datetime import UTC, datetime, timedelta
from typing import cast

from sqlalchemy import and_, delete, exists, func, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from app.modules.document.model import Document
from app.modules.library_item.model import LibraryItem
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_library.model import (
    PaperActivity,
    PaperLibraryMember,
    PaperResearchRelation,
    PaperTag,
    PaperWorkState,
)
from app.modules.paper_library.query import (
    PaperLibraryFilters,
    PaperLibraryView,
    PaperSort,
)

_ACTIVE_ANALYSIS_STATUSES = ("pending", "analyzing")
_WORK_ACTIVITY_KINDS = (
    "reading_progressed",
    "reading_completed",
    "analysis_started",
    "analysis_progressed",
    "analysis_completed",
)


class PaperLibraryRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _filters(
        self,
        view: PaperLibraryView,
        selected: PaperLibraryFilters,
        *,
        exclude: str | None = None,
    ):
        """同组 OR、跨组 AND；exclude 用于生成自排除 facets。"""
        clauses: list[ColumnElement[bool]] = []
        if selected.reading_status and exclude != "reading_status":
            status_filters: list[ColumnElement[bool]] = []
            selected_statuses = set(selected.reading_status)
            if "unread" in selected_statuses:
                status_filters.append(PaperWorkState.id.is_(None))
            explicit_statuses = selected_statuses - {"unread"}
            if explicit_statuses:
                status_filters.append(
                    PaperWorkState.reading_status.in_(explicit_statuses)
                )
            if "unread" in selected_statuses:
                status_filters.append(PaperWorkState.reading_status == "unread")
            clauses.append(or_(*status_filters))
        if selected.paper_types and exclude != "paper_types":
            clauses.append(LibraryItem.paper_type.in_(selected.paper_types))
        if selected.query.strip():
            pattern = f"%{selected.query.strip()}%"
            clauses.append(
                or_(
                    LibraryItem.title.ilike(pattern),
                    LibraryItem.authors.ilike(pattern),
                    LibraryItem.journal.ilike(pattern),
                    LibraryItem.doi.ilike(pattern),
                    LibraryItem.pmid.ilike(pattern),
                    exists(
                        select(PaperTag.id).where(
                            PaperTag.library_item_id == LibraryItem.id,
                            PaperTag.name.ilike(pattern),
                        )
                    ),
                )
            )
        if selected.analysis_status and exclude != "analysis_status":
            latest_id = self._latest_analysis_id()
            analysis_clauses = []
            mapped = {
                "pending": "pending",
                "analyzing": "analyzing",
                "completed": "succeeded",
                "failed": "failed",
                "cancelled": "cancelled",
            }
            for status in selected.analysis_status:
                if status == "not_started":
                    analysis_clauses.append(
                        or_(
                            LibraryItem.document_id.is_(None),
                            ~exists(
                                select(PaperAnalysis.id).where(
                                    PaperAnalysis.document_id == LibraryItem.document_id
                                )
                            ),
                        )
                    )
                elif status in mapped:
                    analysis_clauses.append(
                        exists(
                            select(PaperAnalysis.id).where(
                                PaperAnalysis.id == latest_id,
                                PaperAnalysis.analysis_status == mapped[status],
                            )
                        )
                    )
            if analysis_clauses:
                clauses.append(or_(*analysis_clauses))
        include_roles = selected.research_roles if exclude != "research_roles" else []
        include_research_ids = (
            selected.research_ids if exclude != "research_ids" else []
        )
        if include_roles or include_research_ids:
            relation_filters = [PaperResearchRelation.library_item_id == LibraryItem.id]
            if include_roles:
                relation_filters.append(PaperResearchRelation.role.in_(include_roles))
            if include_research_ids:
                relation_filters.append(
                    PaperResearchRelation.research_context_id.in_(include_research_ids)
                )
            clauses.append(
                exists(select(PaperResearchRelation.id).where(*relation_filters))
            )
        if selected.tags and exclude != "tags":
            clauses.append(
                exists(
                    select(PaperTag.id).where(
                        PaperTag.library_item_id == LibraryItem.id,
                        PaperTag.name.in_(selected.tags),
                    )
                )
            )
        if view is PaperLibraryView.READING:
            clauses.append(PaperWorkState.reading_status == "reading")
        elif view is PaperLibraryView.RECENT:
            cutoff = datetime.now(UTC) - timedelta(days=30)
            clauses.append(
                exists(
                    select(PaperActivity.id).where(
                        PaperActivity.library_item_id == LibraryItem.id,
                        PaperActivity.kind.in_(_WORK_ACTIVITY_KINDS),
                        PaperActivity.created_at >= cutoff,
                    )
                )
            )
        elif view is PaperLibraryView.ANALYZING:
            clauses.append(
                exists(
                    select(PaperAnalysis.id).where(
                        PaperAnalysis.id == self._latest_analysis_id(),
                        PaperAnalysis.analysis_status.in_(_ACTIVE_ANALYSIS_STATUSES),
                    )
                )
            )
        elif view is PaperLibraryView.UNCLASSIFIED:
            relation_exists = exists(
                select(PaperResearchRelation.id).where(
                    PaperResearchRelation.library_item_id == LibraryItem.id
                )
            )
            unassigned_role_exists = exists(
                select(PaperResearchRelation.id).where(
                    PaperResearchRelation.library_item_id == LibraryItem.id,
                    PaperResearchRelation.role.is_(None),
                )
            )
            clauses.append(or_(~relation_exists, unassigned_role_exists))
        return clauses

    @staticmethod
    def _latest_analysis_id():
        latest_analysis = aliased(PaperAnalysis)
        return (
            select(func.max(latest_analysis.id))
            .where(latest_analysis.document_id == LibraryItem.document_id)
            .correlate(LibraryItem)
            .scalar_subquery()
        )

    async def list_items(
        self,
        *,
        view: PaperLibraryView,
        filters: PaperLibraryFilters,
        offset: int,
        limit: int,
        sort: PaperSort,
    ):
        statement = (
            select(LibraryItem, PaperWorkState)
            .join(PaperLibraryMember)
            .outerjoin(PaperWorkState)
            .where(*self._filters(view, filters))
        )
        latest_work_activity_at = (
            select(func.max(PaperActivity.created_at))
            .where(
                PaperActivity.library_item_id == LibraryItem.id,
                PaperActivity.kind.in_(_WORK_ACTIVITY_KINDS),
            )
            .scalar_subquery()
        )
        order = cast(ColumnElement[object], latest_work_activity_at.desc().nullslast())
        if sort is PaperSort.YEAR:
            order = cast(ColumnElement[object], LibraryItem.year.desc().nullslast())
        elif sort is PaperSort.TITLE:
            order = cast(ColumnElement[object], LibraryItem.title.asc().nullslast())
        elif sort is PaperSort.ADDED_AT:
            order = cast(ColumnElement[object], LibraryItem.created_at.desc())
        result = await self.session.execute(
            statement.order_by(order, LibraryItem.id.desc()).offset(offset).limit(limit)
        )
        return list(result.all())

    async def count_items(
        self,
        *,
        view: PaperLibraryView,
        filters: PaperLibraryFilters,
        exclude: str | None = None,
    ) -> int:
        statement = (
            select(func.count(LibraryItem.id))
            .join(PaperLibraryMember)
            .outerjoin(PaperWorkState)
            .where(*self._filters(view, filters, exclude=exclude))
        )
        return (await self.session.execute(statement)).scalar_one()

    async def get_item(self, item_id: int) -> LibraryItem | None:
        result = await self.session.execute(
            select(LibraryItem)
            .join(PaperLibraryMember)
            .where(LibraryItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_membership(self, item_id: int) -> PaperLibraryMember | None:
        result = await self.session.execute(
            select(PaperLibraryMember).where(
                PaperLibraryMember.library_item_id == item_id
            )
        )
        return result.scalar_one_or_none()

    def add_membership(
        self, item_id: int, import_source: str
    ) -> PaperLibraryMember:
        membership = PaperLibraryMember(
            library_item_id=item_id,
            import_source=import_source,
        )
        self.session.add(membership)
        return membership

    async def find_by_identifiers(
        self, pmid: str | None, doi: str | None, document_id: int | None
    ) -> LibraryItem | None:
        clauses = []
        if pmid:
            clauses.append(LibraryItem.pmid == pmid)
        if doi:
            clauses.append(LibraryItem.doi == doi)
        if document_id:
            clauses.append(LibraryItem.document_id == document_id)
        if not clauses:
            return None
        result = await self.session.execute(select(LibraryItem).where(or_(*clauses)))
        matches = list(result.scalars())
        if len(matches) > 1:
            return None
        return matches[0] if matches else None

    async def list_relations(self, item_id: int):
        from app.modules.research_context.model import ResearchContext

        result = await self.session.execute(
            select(PaperResearchRelation, ResearchContext.name)
            .join(ResearchContext)
            .where(PaperResearchRelation.library_item_id == item_id)
            .order_by(PaperResearchRelation.created_at, PaperResearchRelation.id)
        )
        return list(result.all())

    async def relations_for_items(self, item_ids: list[int]):
        from app.modules.research_context.model import ResearchContext

        if not item_ids:
            return {}
        result = await self.session.execute(
            select(PaperResearchRelation, ResearchContext.name)
            .join(ResearchContext)
            .where(PaperResearchRelation.library_item_id.in_(item_ids))
            .order_by(
                PaperResearchRelation.library_item_id,
                PaperResearchRelation.created_at,
                PaperResearchRelation.id,
            )
        )
        grouped: dict[int, list[tuple[PaperResearchRelation, str]]] = {}
        for relation, name in result.all():
            grouped.setdefault(relation.library_item_id, []).append((relation, name))
        return grouped

    async def latest_activities_for_items(
        self, item_ids: list[int]
    ) -> dict[int, PaperActivity]:
        if not item_ids:
            return {}
        latest_activity = aliased(PaperActivity)
        latest_id = (
            select(func.max(latest_activity.id))
            .where(latest_activity.library_item_id == PaperActivity.library_item_id)
            .correlate(PaperActivity)
            .scalar_subquery()
        )
        result = await self.session.execute(
            select(PaperActivity).where(
                PaperActivity.library_item_id.in_(item_ids),
                PaperActivity.id == latest_id,
            )
        )
        return {activity.library_item_id: activity for activity in result.scalars()}

    async def tags_for_items(self, item_ids: list[int]) -> dict[int, list[str]]:
        if not item_ids:
            return {}
        result = await self.session.execute(
            select(PaperTag.library_item_id, PaperTag.name)
            .where(PaperTag.library_item_id.in_(item_ids))
            .order_by(PaperTag.name)
        )
        grouped: dict[int, list[str]] = {}
        for item_id, name in result.all():
            grouped.setdefault(item_id, []).append(name)
        return grouped

    async def replace_tags(self, item_id: int, tags: list[str]) -> None:
        await self.session.execute(
            delete(PaperTag).where(PaperTag.library_item_id == item_id)
        )
        self.session.add_all(
            PaperTag(library_item_id=item_id, name=tag) for tag in tags
        )

    async def documents_by_ids(self, document_ids: list[int]) -> dict[int, Document]:
        if not document_ids:
            return {}
        result = await self.session.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        return {document.id: document for document in result.scalars()}

    async def get_work_state(self, item_id: int) -> PaperWorkState | None:
        result = await self.session.execute(
            select(PaperWorkState).where(PaperWorkState.library_item_id == item_id)
        )
        return result.scalar_one_or_none()

    async def latest_analyses(
        self, document_ids: list[int]
    ) -> dict[int, PaperAnalysis]:
        """每个文档只取最新一次分析，避免列表逐项查询。"""
        if not document_ids:
            return {}
        latest_analysis = aliased(PaperAnalysis)
        latest_id = (
            select(func.max(latest_analysis.id))
            .where(latest_analysis.document_id == PaperAnalysis.document_id)
            .correlate(PaperAnalysis)
            .scalar_subquery()
        )
        result = await self.session.execute(
            select(PaperAnalysis).where(
                PaperAnalysis.document_id.in_(document_ids),
                PaperAnalysis.id == latest_id,
            )
        )
        return {analysis.document_id: analysis for analysis in result.scalars()}

    async def get_relation(
        self, item_id: int, research_id: int
    ) -> PaperResearchRelation | None:
        result = await self.session.execute(
            select(PaperResearchRelation).where(
                and_(
                    PaperResearchRelation.library_item_id == item_id,
                    PaperResearchRelation.research_context_id == research_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def first_relation(self, item_id: int):
        from app.modules.research_context.model import ResearchContext

        result = await self.session.execute(
            select(PaperResearchRelation, ResearchContext.name)
            .join(ResearchContext)
            .where(PaperResearchRelation.library_item_id == item_id)
            .order_by(PaperResearchRelation.created_at)
            .limit(1)
        )
        return result.first()

    async def activities(self, item_id: int, limit: int = 3) -> list[PaperActivity]:
        result = await self.session.execute(
            select(PaperActivity)
            .where(PaperActivity.library_item_id == item_id)
            .order_by(PaperActivity.created_at.desc(), PaperActivity.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def delete_relation_if_version(
        self, relation: PaperResearchRelation, expected_version: int
    ) -> bool:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(PaperResearchRelation).where(
                PaperResearchRelation.id == relation.id,
                PaperResearchRelation.version == expected_version,
            )
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def update_relation_if_version(
        self,
        relation_id: int,
        expected_version: int,
        role: str | None,
        note: str | None,
    ) -> bool:
        result = await self.session.execute(
            update(PaperResearchRelation)
            .where(
                PaperResearchRelation.id == relation_id,
                PaperResearchRelation.version == expected_version,
            )
            .values(
                role=role,
                note=note,
                version=expected_version + 1,
                updated_at=datetime.now(UTC),
            )
        )
        return cast(CursorResult[object], result).rowcount == 1

    async def facet_values(
        self, view: PaperLibraryView, filters: PaperLibraryFilters, group: str
    ):
        base = self._filters(view, filters, exclude=group)
        if group == "reading_status":
            value = func.coalesce(PaperWorkState.reading_status, "unread")
            reading_status_statement = (
                select(value, func.count(LibraryItem.id))
                .select_from(LibraryItem)
                .join(PaperLibraryMember)
                .outerjoin(PaperWorkState)
                .where(*base)
                .group_by(value)
            )
            return list((await self.session.execute(reading_status_statement)).all())
        elif group == "paper_types":
            paper_type_statement = (
                select(LibraryItem.paper_type, func.count(LibraryItem.id))
                .select_from(LibraryItem)
                .join(PaperLibraryMember)
                .outerjoin(PaperWorkState)
                .where(*base, LibraryItem.paper_type.is_not(None))
                .group_by(LibraryItem.paper_type)
            )
            return list((await self.session.execute(paper_type_statement)).all())
        elif group == "research_roles":
            research_role_statement = (
                select(
                    PaperResearchRelation.role,
                    func.count(func.distinct(LibraryItem.id)),
                )
                .select_from(LibraryItem)
                .join(PaperLibraryMember)
                .outerjoin(PaperWorkState)
                .join(PaperResearchRelation)
                .where(*base, PaperResearchRelation.role.is_not(None))
                .group_by(PaperResearchRelation.role)
            )
            return list((await self.session.execute(research_role_statement)).all())
        elif group == "research_ids":
            from app.modules.research_context.model import ResearchContext

            research_context_statement = (
                select(
                    PaperResearchRelation.research_context_id,
                    func.count(func.distinct(LibraryItem.id)),
                    ResearchContext.name,
                )
                .select_from(LibraryItem)
                .join(PaperLibraryMember)
                .outerjoin(PaperWorkState)
                .join(PaperResearchRelation)
                .join(ResearchContext)
                .where(*base)
                .group_by(
                    PaperResearchRelation.research_context_id, ResearchContext.name
                )
            )
            return list((await self.session.execute(research_context_statement)).all())
        elif group == "tags":
            tag_statement = (
                select(PaperTag.name, func.count(func.distinct(LibraryItem.id)))
                .select_from(LibraryItem)
                .join(PaperLibraryMember)
                .outerjoin(PaperWorkState)
                .join(PaperTag)
                .where(*base)
                .group_by(PaperTag.name)
            )
            return list((await self.session.execute(tag_statement)).all())
        else:
            return []

    async def flush(self) -> None:
        await self.session.flush()
