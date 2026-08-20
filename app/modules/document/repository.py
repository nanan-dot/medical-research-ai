"""document — 数据库访问"""

from __future__ import annotations

import builtins

from sqlalchemy import and_, func, not_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.document.model import Document
from app.modules.document_upload.model import DocumentAsset
from app.modules.knowledge_source.model import KnowledgeSource

PARSE_STATUS_SUCCEEDED = "succeeded"
INDEX_STATUS_SUCCEEDED = "succeeded"
PDF_MEDIA_TYPES = frozenset({"application/pdf", "application/x-pdf"})
SUPPORTED_SOURCE_TYPES = frozenset({"local_folder", "obsidian_vault"})


class DocumentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> Document | None:
        result = await self.session.execute(
            select(Document)
            .where(Document.id == id)
            .options(selectinload(Document.asset), selectinload(Document.source))
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        parse_status: str | None = None,
        index_status: str | None = None,
        query: str | None = None,
        research_ready: bool = False,
        previewable_only: bool = False,
        knowledge_source_id: int | None = None,
        needs_attention: bool = False,
        file_type: str | None = None,
        health_status: str | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> list[Document]:
        statement = (
            self._filtered_statement(
                parse_status,
                index_status,
                query,
                research_ready,
                previewable_only,
                knowledge_source_id,
                needs_attention,
                file_type,
                health_status,
            )
            .order_by(*self._sort_columns(sort_by, sort_order))
            .options(selectinload(Document.asset), selectinload(Document.source))
        )
        result = await self.session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(
        self,
        parse_status: str | None = None,
        index_status: str | None = None,
        query: str | None = None,
        research_ready: bool = False,
        previewable_only: bool = False,
        knowledge_source_id: int | None = None,
        needs_attention: bool = False,
        file_type: str | None = None,
        health_status: str | None = None,
    ) -> int:
        statement = (
            self._filtered_statement(
                parse_status,
                index_status,
                query,
                research_ready,
                previewable_only,
                knowledge_source_id,
                needs_attention,
                file_type,
                health_status,
            )
            .with_only_columns(func.count(Document.id))
            .order_by(None)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def list_content_matches(
        self,
        query: str,
        offset: int,
        limit: int,
        knowledge_source_id: int | None,
        file_type: str | None,
        health_status: str | None,
        sort_by: str,
        sort_order: str,
    ) -> builtins.list[tuple[Document, str]]:
        statement = (
            self._content_match_statement(
                query, knowledge_source_id, file_type, health_status
            )
            .with_only_columns(Document, KnowledgeSource.name)
            .order_by(*self._sort_columns(sort_by, sort_order))
            .options(selectinload(Document.asset), selectinload(Document.source))
        )
        result = await self.session.execute(statement.offset(offset).limit(limit))
        return [(row[0], row[1]) for row in result.all()]

    async def count_content_matches(
        self,
        query: str,
        knowledge_source_id: int | None,
        file_type: str | None,
        health_status: str | None,
    ) -> int:
        statement = (
            self._content_match_statement(
                query, knowledge_source_id, file_type, health_status
            )
            .with_only_columns(func.count(Document.id))
            .order_by(None)
        )
        result = await self.session.execute(statement)
        return result.scalar_one()

    @staticmethod
    def _content_match_statement(
        query: str,
        knowledge_source_id: int | None,
        file_type: str | None,
        health_status: str | None,
    ):
        escaped_query = DocumentRepository._escape_like(query.casefold())
        return DocumentRepository._filtered_statement(
            None,
            None,
            None,
            False,
            False,
            knowledge_source_id,
            False,
            file_type,
            health_status,
        ).where(
            Document.parse_status == PARSE_STATUS_SUCCEEDED,
            func.lower(Document.parsed_content).like(f"%{escaped_query}%", escape="\\"),
        )

    @staticmethod
    def _filtered_statement(
        parse_status: str | None,
        index_status: str | None,
        query: str | None,
        research_ready: bool,
        previewable_only: bool,
        knowledge_source_id: int | None,
        needs_attention: bool,
        file_type: str | None,
        health_status: str | None,
    ):
        # “全部文档”必须与知识来源汇总使用同一范围；历史孤儿记录不能静默混入。
        statement = (
            select(Document)
            .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
            .outerjoin(DocumentAsset)
            .where(KnowledgeSource.source_type.in_(SUPPORTED_SOURCE_TYPES))
        )
        if parse_status is not None:
            statement = statement.where(Document.parse_status == parse_status)
        if index_status is not None:
            statement = statement.where(Document.index_status == index_status)
        if knowledge_source_id is not None:
            statement = statement.where(
                Document.knowledge_source_id == knowledge_source_id
            )
        if file_type is not None:
            filename = func.lower(func.coalesce(DocumentAsset.original_filename, Document.file_path))
            if file_type == "markdown":
                statement = statement.where(
                    or_(filename.like("%.md"), filename.like("%.markdown"))
                )
            elif file_type == "other":
                statement = statement.where(
                    ~or_(
                        *[
                            filename.like(f"%{suffix}")
                            for suffix in (".pdf", ".pptx", ".docx", ".md", ".markdown", ".txt")
                        ]
                    )
                )
            else:
                statement = statement.where(filename.like(f"%.{file_type}"))
        if query is not None:
            escaped_query = DocumentRepository._escape_like(query.casefold())
            pattern = f"%{escaped_query}%"
            statement = statement.where(
                or_(
                    func.lower(Document.file_path).like(pattern, escape="\\"),
                    func.lower(DocumentAsset.original_filename).like(
                        pattern, escape="\\"
                    ),
                )
            )
        if research_ready:
            statement = statement.where(
                Document.parse_status == PARSE_STATUS_SUCCEEDED,
                Document.index_status == INDEX_STATUS_SUCCEEDED,
                Document.paperqa_index_key.is_not(None),
                Document.paperqa_index_key != "",
            )
        if previewable_only:
            # 上传模块只认可这两个 PDF MIME 类型；不按文件扩展名推断可预览性。
            statement = statement.where(DocumentAsset.media_type.in_(PDF_MEDIA_TYPES))
        if needs_attention:
            statement = statement.where(DocumentRepository._needs_attention_predicate())
        if health_status is not None:
            statement = statement.where(
                DocumentRepository._health_status_predicate(health_status)
            )
        return statement

    @staticmethod
    def _needs_attention_predicate():
        return or_(
            Document.parse_status == "failed",
            Document.index_status.in_(("failed", "outdated")),
            Document.error_code == "source_file_missing",
            KnowledgeSource.sync_status == "unavailable",
        )

    @staticmethod
    def _health_status_predicate(health_status: str):
        needs_attention = DocumentRepository._needs_attention_predicate()
        if health_status == "needs_attention":
            return needs_attention
        if health_status == "available":
            return and_(
                Document.parse_status == PARSE_STATUS_SUCCEEDED,
                Document.index_status == INDEX_STATUS_SUCCEEDED,
                not_(needs_attention),
            )
        return and_(
            not_(needs_attention),
            or_(
                Document.parse_status.in_(("pending", "parsing")),
                Document.index_status.in_(("pending", "indexing")),
            ),
        )

    @staticmethod
    def _sort_columns(sort_by: str, sort_order: str):
        descending = sort_order == "desc"
        column = Document.modified_time if sort_by == "updated_at" else (Document.file_size if sort_by == "file_size" else func.lower(func.coalesce(DocumentAsset.original_filename, Document.file_path)))
        return (column.desc() if descending else column.asc(), Document.id.desc() if descending else Document.id.asc())

    @staticmethod
    def _escape_like(value: str) -> str:
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    async def list_by_source(self, knowledge_source_id: int) -> builtins.list[Document]:
        result = await self.session.execute(
            select(Document).where(Document.knowledge_source_id == knowledge_source_id)
        )
        return list(result.scalars().all())

    async def list_library_documents(self) -> builtins.list[Document]:
        """Return only documents that belong to a current supported knowledge source."""
        result = await self.session.execute(
            select(Document)
            .join(KnowledgeSource, Document.knowledge_source_id == KnowledgeSource.id)
            .where(KnowledgeSource.source_type.in_(SUPPORTED_SOURCE_TYPES))
            .order_by(Document.id)
            .options(selectinload(Document.asset), selectinload(Document.source))
        )
        return list(result.scalars().all())

    async def list_all(self) -> builtins.list[Document]:
        """Return all documents for cross-module metadata matching, including legacy rows."""
        result = await self.session.execute(
            select(Document).order_by(Document.id).options(selectinload(Document.asset))
        )
        return list(result.scalars().all())

    async def create(self, entity: Document) -> Document:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: Document) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def save(self, entity: Document) -> Document:
        await self.session.flush()
        return entity
