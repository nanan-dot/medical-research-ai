"""论文库业务编排与一致性规则。"""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.library_item.model import LibraryItem
from app.modules.library_item.schema import FulltextStatus
from app.modules.paper_analysis.model import PaperAnalysis
from app.modules.paper_library.activity_service import PaperActivityService
from app.modules.paper_library.analysis_progress import project_analysis_progress
from app.modules.paper_library.identity_service import require_identity
from app.modules.paper_library.metadata_service import (
    MetadataClient,
    PaperMetadataService,
)
from app.modules.paper_library.model import PaperResearchRelation, PaperWorkState
from app.modules.paper_library.query import (
    AnalysisStatus,
    PaperLibraryFilters,
    PaperLibraryView,
    PaperSort,
)
from app.modules.paper_library.repository import PaperLibraryRepository
from app.modules.paper_library.schema import (
    ActivityRead,
    FacetValue,
    PaperAddRequest,
    PaperAddResult,
    PaperItemPage,
    PaperItemRead,
    PaperLibraryFacets,
    PaperLibrarySummary,
    PaperOverviewRead,
    ReadingStateRead,
    ReadingStateUpdate,
    ReadingStatus,
    ResearchRelationRead,
    ResearchRelationUpdate,
    ResearchRole,
    WorkEntryRead,
)
from app.modules.paper_library.work_projection import project_work_entries
from app.modules.research_context.model import ResearchContext

_EXTERNAL_IDENTIFIER_SOURCE = "external_identifier"
_RESOURCE_LIBRARY_SOURCE = "resource_library"


class PaperLibraryService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        metadata_client_factory: Callable[[], MetadataClient] | None = None,
    ):
        self.session = session
        self.repo = PaperLibraryRepository(session)
        self.activities = PaperActivityService(session)
        self.documents = DocumentRepository(session)
        self.metadata = PaperMetadataService(
            session, client_factory=metadata_client_factory
        )

    async def summary(self) -> PaperLibrarySummary:
        async def count(view: PaperLibraryView) -> int:
            return await self.repo.count_items(view=view, filters=PaperLibraryFilters())

        return PaperLibrarySummary(
            all=await count(PaperLibraryView.ALL),
            recent=await count(PaperLibraryView.RECENT),
            reading=await count(PaperLibraryView.READING),
            analyzing=await count(PaperLibraryView.ANALYZING),
            unclassified=await count(PaperLibraryView.UNCLASSIFIED),
        )

    async def list_items(
        self,
        *,
        view: PaperLibraryView,
        filters: PaperLibraryFilters,
        offset: int,
        limit: int,
        sort: PaperSort,
    ) -> PaperItemPage:
        rows = await self.repo.list_items(
            view=view, filters=filters, offset=offset, limit=limit, sort=sort
        )
        item_ids = [item.id for item, _ in rows]
        document_ids = [
            item.document_id for item, _ in rows if item.document_id is not None
        ]
        analyses = await self.repo.latest_analyses(document_ids)
        relations = await self.repo.relations_for_items(item_ids)
        activities = await self.repo.latest_activities_for_items(item_ids)
        tags = await self.repo.tags_for_items(item_ids)
        documents = await self.repo.documents_by_ids(document_ids)
        items: list[PaperItemRead] = []
        for item, state in rows:
            relation = None
            item_relations = relations.get(item.id, [])
            if item_relations:
                relation_model, research_name = self._select_primary_relation(
                    item_relations, filters
                )
                relation = self._relation_read(relation_model, research_name)
            activity_model = activities.get(item.id)
            item_read = self._item_read(
                item,
                state,
                relation,
                len(item_relations),
                analyses.get(item.document_id) if item.document_id else None,
                documents.get(item.document_id) if item.document_id else None,
                tags.get(item.id, []),
            )
            item_read.recent_activity = (
                ActivityRead.model_validate(activity_model, from_attributes=True)
                if activity_model
                else None
            )
            items.append(item_read)
        total = await self.repo.count_items(view=view, filters=filters)
        return PaperItemPage(items=items, total=total, offset=offset, limit=limit)

    async def facets(
        self, view: PaperLibraryView, filters: PaperLibraryFilters
    ) -> PaperLibraryFacets:
        async def values(group: str) -> list[FacetValue]:
            rows = await self.repo.facet_values(view, filters, group)
            return [
                FacetValue(
                    value=str(row[0]),
                    count=row[1],
                    label=(row[2] if len(row) > 2 else None),
                )
                for row in rows
            ]

        analysis_values = []
        for status in AnalysisStatus:
            selected = replace(filters, analysis_status=[status.value])
            analysis_values.append(
                FacetValue(
                    value=status.value,
                    count=await self.repo.count_items(view=view, filters=selected),
                )
            )
        return PaperLibraryFacets(
            reading_status=await values("reading_status"),
            analysis_status=analysis_values,
            paper_types=await values("paper_types"),
            research_roles=await values("research_roles"),
            research_contexts=await values("research_ids"),
            tags=await values("tags"),
        )

    async def update_tags(self, item_id: int, tags: list[str]) -> list[str]:
        if await self.repo.get_item(item_id) is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        await self.repo.replace_tags(item_id, tags)
        self.activities.record(item_id, "tags_changed", ", ".join(tags))
        await self.repo.flush()
        return tags

    async def update_reading_state(
        self, item_id: int, payload: ReadingStateUpdate
    ) -> ReadingStateRead:
        if await self.repo.get_item(item_id) is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        state = await self._get_or_create_work_state(item_id)
        if (
            state.reading_status == payload.status.value
            and state.reading_progress_percent == payload.progress_percent
            and state.current_section == payload.current_section
        ):
            return ReadingStateRead.model_validate(state, from_attributes=True)
        now = datetime.now(UTC)
        state.reading_status = payload.status.value
        state.reading_progress_percent = payload.progress_percent
        state.current_section = payload.current_section
        state.updated_at = now
        if payload.status is ReadingStatus.UNREAD:
            state.last_read_at = None
            state.last_work_kind = "analysis" if state.last_analysis_at else None
            kind = "reading_reset"
        else:
            state.last_read_at = now
            state.last_work_kind = "reading"
            kind = (
                "reading_completed"
                if payload.status is ReadingStatus.READ
                else "reading_progressed"
            )
        self.activities.record(item_id, kind, payload.current_section)
        await self.repo.flush()
        return ReadingStateRead.model_validate(state, from_attributes=True)

    async def activities_for(self, item_id: int) -> list[ActivityRead]:
        if await self.repo.get_item(item_id) is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        return [
            ActivityRead.model_validate(row, from_attributes=True)
            for row in await self.repo.activities(item_id)
        ]

    async def overview(self, item_id: int) -> PaperOverviewRead:
        item = await self.repo.get_item(item_id)
        if item is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        state = await self.repo.get_work_state(item_id)
        relation_rows = await self.repo.list_relations(item_id)
        relations = [self._relation_read(model, name) for model, name in relation_rows]
        activities = await self.activities_for(item_id)
        analyses = await self.repo.latest_analyses(
            [item.document_id] if item.document_id else []
        )
        documents = await self.repo.documents_by_ids(
            [item.document_id] if item.document_id else []
        )
        tags = await self.repo.tags_for_items([item.id])
        item_read = self._item_read(
            item,
            state,
            relations[0] if relations else None,
            len(relations),
            analyses.get(item.document_id) if item.document_id else None,
            documents.get(item.document_id) if item.document_id else None,
            tags.get(item.id, []),
        )
        return PaperOverviewRead(
            **item_read.model_dump(), relations=relations, activities=activities
        )

    async def add(self, payload: PaperAddRequest) -> PaperAddResult:
        doi, pmid = require_identity(payload.doi, payload.pmid)
        document = None
        if payload.document_id is not None:
            document = await self.documents.get(payload.document_id)
            if document is None:
                raise NotFoundError(f"Document not found: {payload.document_id}")
        existing = await self.repo.find_by_identifiers(pmid, doi, payload.document_id)
        if existing is not None:
            linked_document = False
            if document and existing.document_id is None:
                existing.document_id = document.id
                existing.fulltext_status = FulltextStatus.LOCAL_PDF_AVAILABLE.value
                existing.fulltext_status_reason = (
                    "Local document linked through paper-library add"
                )
                existing.updated_at = datetime.now(UTC)
                linked_document = True
            was_added = await self._ensure_membership(
                existing.id,
                self._import_source(document),
            )
            if was_added:
                self.activities.record(existing.id, "paper_added", "paper_library")
            await self.repo.flush()
            return PaperAddResult(
                item=self._item_read(existing, None, None, 0),
                outcome=(
                    "linked"
                    if linked_document
                    else "created"
                    if was_added
                    else "already_exists"
                ),
            )
        if doi is None and pmid is None and document is None:
            raise ConflictError("无法识别论文身份")
        item = LibraryItem(
            pmid=pmid,
            doi=doi,
            title=document.parsed_title if document else None,
            document_id=document.id if document else None,
            source_search_id=None,
            fulltext_status=(
                FulltextStatus.LOCAL_PDF_AVAILABLE.value
                if document
                else FulltextStatus.METADATA_ONLY.value
            ),
            fulltext_status_reason=(
                "Document linked; metadata awaits verified extraction"
                if document
                else "Identifier saved; metadata awaits verified retrieval"
            ),
        )
        try:
            async with self.session.begin_nested():
                self.session.add(item)
                await self.repo.flush()
                self.repo.add_membership(item.id, self._import_source(document))
                await self.repo.flush()
        except IntegrityError:
            # 唯一索引是并发幂等的最终裁判；保存点避免污染外层请求事务。
            existing = await self.repo.find_by_identifiers(
                pmid, doi, payload.document_id
            )
            if existing is not None:
                return PaperAddResult(
                    item=self._item_read(existing, None, None, 0),
                    outcome="already_exists",
                )
            raise ConflictError("论文标识与现有记录冲突，请刷新后重试")
        self.activities.record(item.id, "paper_added", "paper_library")
        await self.repo.flush()
        return PaperAddResult(
            item=self._item_read(item, None, None, 0), outcome="created"
        )

    @staticmethod
    def _import_source(document: Document | None) -> str:
        return _RESOURCE_LIBRARY_SOURCE if document is not None else _EXTERNAL_IDENTIFIER_SOURCE

    async def _ensure_membership(self, item_id: int, import_source: str) -> bool:
        """仅在用户主动导入时创建成员关系，历史收藏不会被反向纳入。"""
        if await self.repo.get_membership(item_id) is not None:
            return False
        try:
            async with self.session.begin_nested():
                self.repo.add_membership(item_id, import_source)
                await self.repo.flush()
        except IntegrityError:
            # 唯一约束处理双窗口同时把同一资料加入论文库的场景。
            if await self.repo.get_membership(item_id) is not None:
                return False
            raise ConflictError("论文库成员创建冲突，请刷新后重试")
        return True

    async def refresh_metadata(self, item_id: int) -> PaperItemRead:
        item = await self.repo.get_item(item_id)
        if item is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        if not item.pmid and not item.doi:
            raise ConflictError("该论文没有可用于可信元数据检索的 DOI 或 PMID")
        await self.metadata.enrich(item)
        state = await self.repo.get_work_state(item_id)
        analyses = await self.repo.latest_analyses(
            [item.document_id] if item.document_id else []
        )
        documents = await self.repo.documents_by_ids(
            [item.document_id] if item.document_id else []
        )
        relations = await self.repo.list_relations(item_id)
        tags = await self.repo.tags_for_items([item_id])
        primary = (
            self._relation_read(*relations[0]) if relations else None
        )
        return self._item_read(
            item,
            state,
            primary,
            len(relations),
            analyses.get(item.document_id) if item.document_id else None,
            documents.get(item.document_id) if item.document_id else None,
            tags.get(item_id, []),
        )

    async def upsert_relation(
        self, item_id: int, research_id: int, payload: ResearchRelationUpdate
    ) -> ResearchRelationRead:
        if await self.repo.get_item(item_id) is None:
            raise NotFoundError(f"LibraryItem not found: {item_id}")
        research = await self.session.get(ResearchContext, research_id)
        if research is None:
            raise NotFoundError(f"ResearchContext not found: {research_id}")
        relation = await self.repo.get_relation(item_id, research_id)
        if relation is None:
            relation = PaperResearchRelation(
                library_item_id=item_id,
                research_context_id=research_id,
                role=payload.role.value if payload.role else None,
                note=payload.note,
                version=1,
            )
            try:
                async with self.session.begin_nested():
                    self.session.add(relation)
                    await self.repo.flush()
            except IntegrityError:
                raise ConflictError("论文研究关系已由其他操作创建，请刷新后重试")
        else:
            if payload.expected_version != relation.version:
                raise ConflictError("论文研究关系已被其他操作更新，请刷新后重试")
            if not await self.repo.update_relation_if_version(
                relation.id,
                payload.expected_version,
                payload.role.value if payload.role else None,
                payload.note,
            ):
                raise ConflictError("论文研究关系已被其他操作更新，请刷新后重试")
            relation.role = payload.role.value if payload.role else None
            relation.note = payload.note
            relation.version = payload.expected_version + 1
        self.activities.record(item_id, "research_relation_changed", research.name)
        await self.repo.flush()
        return self._relation_read(relation, research.name)

    async def delete_relation(
        self, item_id: int, research_id: int, expected_version: int
    ) -> None:
        relation = await self.repo.get_relation(item_id, research_id)
        if relation is None:
            raise NotFoundError("论文研究关系不存在")
        if not await self.repo.delete_relation_if_version(relation, expected_version):
            raise ConflictError("论文研究关系已被其他操作更新，请刷新后重试")
        self.activities.record(item_id, "research_relation_changed", "relation_removed")
        await self.repo.flush()

    @staticmethod
    def _relation_read(
        relation: PaperResearchRelation, research_name: str
    ) -> ResearchRelationRead:
        return ResearchRelationRead(
            research_context_id=relation.research_context_id,
            research_name=research_name,
            role=ResearchRole(relation.role) if relation.role else None,
            note=relation.note,
            version=relation.version,
        )

    async def _get_or_create_work_state(self, item_id: int) -> PaperWorkState:
        state = await self.repo.get_work_state(item_id)
        if state is not None:
            return state
        candidate = PaperWorkState(library_item_id=item_id)
        try:
            async with self.session.begin_nested():
                self.session.add(candidate)
                await self.repo.flush()
        except IntegrityError:
            # 首次阅读可能被两个窗口同时触发；唯一约束后重新读取赢家即可。
            state = await self.repo.get_work_state(item_id)
            if state is not None:
                return state
            raise ConflictError("阅读状态创建冲突，请重试")
        return candidate

    @staticmethod
    def _item_read(
        item: LibraryItem,
        state: PaperWorkState | None,
        relation: ResearchRelationRead | None,
        relation_count: int,
        analysis: PaperAnalysis | None = None,
        document=None,
        tags: list[str] | None = None,
    ) -> PaperItemRead:
        analysis_status, analysis_progress = PaperLibraryService._analysis_projection(
            analysis
        )
        can_read = document is not None and document.parse_status == "succeeded"
        can_analyze = can_read and document.index_status == "succeeded"
        reading_reason = None if can_read else "全文尚未解析完成"
        analysis_reason = (
            None if can_analyze else (
                reading_reason if not can_read else "全文索引尚未完成"
            )
        )
        work = project_work_entries(
            state,
            analysis_status=analysis_status,
            can_read=can_read,
            can_analyze=can_analyze,
            reading_reason=reading_reason,
            analysis_reason=analysis_reason,
        )
        return PaperItemRead(
            id=item.id,
            pmid=item.pmid,
            doi=item.doi,
            title=item.title,
            authors=item.authors,
            journal=item.journal,
            year=item.year,
            paper_type=item.paper_type,
            journal_quartile=item.journal_quartile,
            journal_quartile_source=item.journal_quartile_source,
            journal_quartile_year=item.journal_quartile_year,
            metadata_status=item.metadata_status,
            metadata_source=item.metadata_source,
            metadata_retryable=item.metadata_status in {"pending", "running", "failed"},
            metadata_error_code=item.metadata_error_code,
            document_id=item.document_id,
            fulltext_status=item.fulltext_status,
            reading_status=ReadingStatus(state.reading_status)
            if state
            else ReadingStatus.UNREAD,
            reading_progress_percent=state.reading_progress_percent if state else 0,
            current_section=state.current_section if state else None,
            analysis_status=analysis_status,
            analysis_progress=analysis_progress,
            primary_relation=relation,
            additional_relation_count=max(0, relation_count - 1),
            tags=tags or [],
            can_read=can_read,
            can_analyze=can_analyze,
            capability_reason=analysis_reason,
            preferred_work_action=work.preferred_action,
            last_work_at=work.last_work_at,
            reading_entry=WorkEntryRead(
                action=work.reading.action,
                enabled=work.reading.enabled,
                reason=work.reading.reason,
            ),
            analysis_entry=WorkEntryRead(
                action=work.analysis.action,
                enabled=work.analysis.enabled,
                reason=work.analysis.reason,
            ),
        )

    @staticmethod
    def _analysis_projection(
        analysis: PaperAnalysis | None,
    ) -> tuple[str, dict[str, int] | None]:
        if analysis is None:
            return "not_started", None
        status_map = {
            "pending": "pending",
            "analyzing": "analyzing",
            "succeeded": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        status = status_map.get(analysis.analysis_status, "unknown")
        progress = project_analysis_progress(analysis)
        return (
            status,
            {"completed": progress.completed, "total": progress.total}
            if progress
            else None,
        )

    @staticmethod
    def _select_primary_relation(
        rows: list[tuple[PaperResearchRelation, str]],
        filters: PaperLibraryFilters,
    ) -> tuple[PaperResearchRelation, str]:
        """筛选命中关系必须成为列表主关系，避免卡片展示另一个研究的角色。"""
        for relation, name in rows:
            matches_research = (
                not filters.research_ids
                or relation.research_context_id in filters.research_ids
            )
            matches_role = (
                not filters.research_roles or relation.role in filters.research_roles
            )
            if matches_research and matches_role:
                return relation, name
        return rows[0]
