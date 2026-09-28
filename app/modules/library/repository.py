"""SQL queries and aggregates for the unified research-resource library."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import and_, case, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.document.model import Document
from app.modules.document_upload.model import DocumentAsset
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.library.model import DocumentAccess, ZoteroCollection, ZoteroLibrary


@dataclass(frozen=True)
class LibraryQuery:
    """A bounded, typed query object shared by list and facet operations."""

    q: str | None = None
    source_ids: tuple[int, ...] = ()
    source_types: tuple[str, ...] = ()
    file_types: tuple[str, ...] = ()
    statuses: tuple[str, ...] = ()
    updated_from: object | None = None
    updated_to: object | None = None
    tree_node: tuple[int, str] | None = None


class LibraryRepository:
    """Keep list predicates, summary aggregation and storage reads SQL-backed."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _ai_available_predicate():
        return and_(
            func.coalesce(Document.metadata_only, False).is_(False),
            Document.parse_status == "succeeded",
            Document.index_status == "succeeded",
            Document.paperqa_index_key.is_not(None),
            Document.paperqa_index_key != "",
        )

    @staticmethod
    def _needs_attention_predicate():
        return func.coalesce(or_(
            Document.metadata_only.is_(True),
            Document.parse_status == "failed",
            Document.index_status.in_(("failed", "outdated")),
            Document.scan_state == "outdated",
            Document.error_code.in_(("source_file_missing", "document_unavailable")),
            KnowledgeSource.sync_status == "unavailable",
        ), False)

    @classmethod
    def _processing_predicate(cls):
        return and_(
            not_(cls._needs_attention_predicate()),
            or_(
                Document.parse_status.in_(("pending", "parsing")),
                Document.index_status.in_(("pending", "indexing")),
            ),
        )

    @classmethod
    def _status_predicate(cls, statuses: Iterable[str]):
        predicates = []
        for status in statuses:
            if status == "ai_available":
                predicates.append(cls._ai_available_predicate())
            elif status in {"processing", "needs_processing"}:
                predicates.append(cls._processing_predicate())
            elif status == "outdated":
                predicates.append(
                    or_(Document.index_status == "outdated", Document.scan_state == "outdated")
                )
            elif status == "metadata_only":
                predicates.append(Document.metadata_only.is_(True))
            elif status == "needs_attention":
                predicates.append(cls._needs_attention_predicate())
        return or_(*predicates) if predicates else None

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    @staticmethod
    def _file_type_expression():
        filename = func.lower(func.coalesce(DocumentAsset.original_filename, Document.file_path))
        return case(
            (filename.like("%.pdf"), "pdf"),
            (filename.like("%.docx"), "docx"),
            (filename.like("%.pptx"), "pptx"),
            (or_(filename.like("%.md"), filename.like("%.markdown")), "markdown"),
            (filename.like("%.txt"), "txt"),
            else_="other",
        )

    @classmethod
    def _base_statement(cls):
        return select(Document).join(
            KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id
        ).outerjoin(DocumentAsset)

    @classmethod
    def _filtered_statement(cls, query: LibraryQuery, *, omit: str | None = None):
        statement = cls._base_statement()
        if query.q:
            pattern = f"%{cls._escape_like(query.q.casefold())}%"
            statement = statement.where(
                or_(
                    func.lower(Document.file_path).like(pattern, escape="\\"),
                    func.lower(Document.parsed_title).like(pattern, escape="\\"),
                    func.lower(Document.parsed_content).like(pattern, escape="\\"),
                    func.lower(DocumentAsset.original_filename).like(pattern, escape="\\"),
                    func.lower(KnowledgeSource.name).like(pattern, escape="\\"),
                )
            )
        if query.source_ids and omit != "source_ids":
            statement = statement.where(Document.knowledge_source_id.in_(query.source_ids))
        if query.source_types and omit != "source_types":
            statement = statement.where(KnowledgeSource.source_type.in_(query.source_types))
        if query.file_types and omit != "file_types":
            statement = statement.where(cls._file_type_expression().in_(query.file_types))
        if query.statuses and omit != "statuses":
            predicate = cls._status_predicate(query.statuses)
            if predicate is not None:
                statement = statement.where(predicate)
        if query.updated_from is not None:
            statement = statement.where(Document.modified_time >= query.updated_from)
        if query.updated_to is not None:
            statement = statement.where(Document.modified_time <= query.updated_to)
        if query.tree_node is not None:
            source_id, relative_prefix = query.tree_node
            prefix = relative_prefix.casefold().strip("/")
            statement = statement.where(Document.knowledge_source_id == source_id)
            if prefix:
                statement = statement.where(
                    or_(
                        func.lower(Document.normalized_file_path) == prefix,
                        func.lower(Document.normalized_file_path).like(
                            f"{cls._escape_like(prefix)}/%", escape="\\"
                        ),
                    )
                )
        return statement

    async def list_documents(
        self, query: LibraryQuery, sort_by: str, sort_order: str, offset: int, limit: int
    ) -> list[Document]:
        descending = sort_order == "desc"
        filename = func.lower(func.coalesce(DocumentAsset.original_filename, Document.file_path))
        status_order = case(
            (self._ai_available_predicate(), 0),
            (self._processing_predicate(), 1),
            else_=2,
        )
        order_column = {
            "updated_at": Document.modified_time,
            "name": filename,
            "file_size": Document.file_size,
            "source_name": func.lower(KnowledgeSource.name),
            "status": status_order,
            "last_opened": DocumentAccess.last_opened_at,
        }.get(sort_by, Document.modified_time)
        statement = self._filtered_statement(query)
        if sort_by == "last_opened":
            statement = statement.outerjoin(DocumentAccess).order_by(
                DocumentAccess.last_opened_at.is_(None),
                order_column.desc() if descending else order_column.asc(),
                Document.id.desc() if descending else Document.id.asc(),
            )
        else:
            statement = statement.order_by(
                order_column.desc() if descending else order_column.asc(),
                Document.id.desc() if descending else Document.id.asc(),
            )
        result = await self.session.execute(
            statement.options(selectinload(Document.asset), selectinload(Document.source))
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def count_documents(self, query: LibraryQuery) -> int:
        statement = self._filtered_statement(query).with_only_columns(func.count(Document.id)).order_by(None)
        return int((await self.session.execute(statement)).scalar_one())

    async def list_recent_documents(self, offset: int, limit: int) -> list[Document]:
        """Return only explicitly opened documents; paging happens in SQL."""
        result = await self.session.execute(
            self._base_statement()
            .join(DocumentAccess, DocumentAccess.document_id == Document.id)
            .options(selectinload(Document.asset), selectinload(Document.source))
            .order_by(DocumentAccess.last_opened_at.desc(), Document.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().unique().all())

    async def count_recent_documents(self) -> int:
        return int(
            (
                await self.session.scalar(
                    select(func.count(DocumentAccess.id)).select_from(DocumentAccess)
                )
            )
            or 0
        )

    async def get_document(self, document_id: int) -> Document | None:
        result = await self.session.execute(
            self._base_statement()
            .where(Document.id == document_id)
            .options(selectinload(Document.asset), selectinload(Document.source))
        )
        return result.scalar_one_or_none()

    async def documents_for_tree(self) -> list[Document]:
        result = await self.session.execute(
            self._base_statement().options(selectinload(Document.asset), selectinload(Document.source))
        )
        return list(result.scalars().unique().all())

    async def source_rows(self) -> list[KnowledgeSource]:
        result = await self.session.execute(select(KnowledgeSource).order_by(KnowledgeSource.id))
        return list(result.scalars().all())

    async def zotero_collections_by_source(self) -> dict[int, list[ZoteroCollection]]:
        """Load every cached collection in one set-based query for tree rendering."""
        result = await self.session.execute(
            select(ZoteroLibrary.knowledge_source_id, ZoteroCollection)
            .join(
                ZoteroCollection,
                ZoteroCollection.zotero_library_id == ZoteroLibrary.id,
            )
            .where(ZoteroCollection.is_deleted.is_(False))
            .order_by(
                ZoteroLibrary.knowledge_source_id,
                ZoteroCollection.parent_key,
                ZoteroCollection.name,
                ZoteroCollection.collection_key,
            )
        )
        grouped: dict[int, list[ZoteroCollection]] = {}
        for source_id, collection in result:
            grouped.setdefault(int(source_id), []).append(collection)
        return grouped

    async def summary_values(self) -> dict[str, int]:
        ai_available = self._ai_available_predicate()
        needs_attention = self._needs_attention_predicate()
        processing = self._processing_predicate()
        unsupported = Document.error_code.in_(("unsupported_format", "legacy_converter_unavailable"))
        unavailable = Document.error_code.in_(("source_file_missing", "document_unavailable"))
        index_failed = Document.index_status == "failed"
        result = await self.session.execute(
            select(
                func.count(Document.id).label("total"),
                func.coalesce(func.sum(case((Document.parse_status == "succeeded", 1), else_=0)), 0).label("processed"),
                func.coalesce(func.sum(case((ai_available, 1), else_=0)), 0).label("ai_available"),
                func.coalesce(func.sum(case((processing, 1), else_=0)), 0).label("processing"),
                func.coalesce(func.sum(case((needs_attention, 1), else_=0)), 0).label("needs_attention"),
                func.coalesce(func.sum(case((Document.parse_status == "failed", 1), else_=0)), 0).label("parse_failed"),
                func.coalesce(func.sum(case((unsupported, 1), else_=0)), 0).label("unsupported_format"),
                func.coalesce(func.sum(case((unavailable, 1), else_=0)), 0).label("unavailable_file"),
                func.coalesce(func.sum(case((index_failed, 1), else_=0)), 0).label("index_failed"),
                func.coalesce(
                    func.sum(
                        case((and_(needs_attention, not_(or_(Document.parse_status == "failed", unsupported, unavailable, index_failed))), 1), else_=0)
                    ),
                    0,
                ).label("other"),
            ).select_from(Document).join(KnowledgeSource)
        )
        row = result.one()._mapping
        return {name: int(row[name]) for name in row}

    async def source_type_counts(self) -> list[tuple[str, int]]:
        result = await self.session.execute(
            select(KnowledgeSource.source_type, func.count(KnowledgeSource.id))
            .group_by(KnowledgeSource.source_type)
            .order_by(KnowledgeSource.source_type)
        )
        return [(str(source_type), int(count)) for source_type, count in result]

    async def facets(self, query: LibraryQuery) -> dict[str, list[tuple[str, int]]]:
        """Return self-excluding dimensions; each query remains set-based and unpaged."""
        source_statement = self._filtered_statement(query, omit="source_ids").with_only_columns(
            KnowledgeSource.name, func.count(Document.id)
        ).group_by(KnowledgeSource.id, KnowledgeSource.name).order_by(func.lower(KnowledgeSource.name), KnowledgeSource.id)
        source_type_statement = self._filtered_statement(query, omit="source_types").with_only_columns(
            KnowledgeSource.source_type, func.count(Document.id)
        ).group_by(KnowledgeSource.source_type).order_by(KnowledgeSource.source_type)
        file_statement = self._filtered_statement(query, omit="file_types").with_only_columns(
            self._file_type_expression().label("value"), func.count(Document.id)
        ).group_by("value").order_by("value")
        status_statement = self._filtered_statement(query, omit="statuses").with_only_columns(
            Document.id, self._ai_available_predicate().label("is_ai"), self._processing_predicate().label("is_processing"), self._needs_attention_predicate().label("is_attention"), Document.metadata_only.label("is_metadata"),
        )
        source_rows, source_type_rows, file_rows, status_rows = await self.session.execute(source_statement), await self.session.execute(source_type_statement), await self.session.execute(file_statement), await self.session.execute(status_statement)
        status_counts = {"ai_available": 0, "processing": 0, "needs_attention": 0, "metadata_only": 0, "outdated": 0}
        for _, is_ai, is_processing, is_attention, is_metadata in status_rows:
            if is_ai:
                status_counts["ai_available"] += 1
            elif is_metadata:
                status_counts["metadata_only"] += 1
            elif is_processing:
                status_counts["processing"] += 1
            elif is_attention:
                status_counts["needs_attention"] += 1
        return {
            "sources": [(str(value), int(count)) for value, count in source_rows],
            "source_types": [(str(value), int(count)) for value, count in source_type_rows],
            "file_types": [(str(value), int(count)) for value, count in file_rows],
            "statuses": [(value, count) for value, count in status_counts.items() if count],
        }

    async def access_by_document_ids(self, document_ids: list[int]) -> dict[int, DocumentAccess]:
        if not document_ids:
            return {}
        result = await self.session.execute(
            select(DocumentAccess).where(DocumentAccess.document_id.in_(document_ids))
        )
        return {access.document_id: access for access in result.scalars()}

    async def storage_values(self) -> tuple[int, int]:
        managed = await self.session.scalar(select(func.coalesce(func.sum(DocumentAsset.byte_size), 0)))
        external = await self.session.scalar(
            select(func.coalesce(func.sum(Document.file_size), 0))
            .select_from(Document)
            .outerjoin(DocumentAsset)
            .where(DocumentAsset.id.is_(None))
        )
        return int(managed or 0), int(external or 0)

    async def find_asset_document_by_sha256(self, sha256: str) -> int | None:
        return await self.session.scalar(
            select(DocumentAsset.document_id).where(DocumentAsset.sha256 == sha256).limit(1)
        )
