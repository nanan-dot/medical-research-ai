"""Document status, retry, and stale-task management."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.common.logger import logger
from app.modules.document.model import Document
from app.modules.document.parsers.base import DocumentParserError
from app.modules.document.parsers.factory import create_parser
from app.modules.document.parsers.schemas import ParsedContentSummary, ParsedDocument
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import (
    ContentLocatorType,
    ContentSearchPage,
    ContentSearchResult,
    DocumentFileType,
    DocumentHealthStatus,
    DocumentPage,
    DocumentRead,
    DocumentStatistics,
    IndexStatus,
    ParseStatus,
)
from app.modules.document.state_machine import (
    ensure_index_transition,
    ensure_parse_transition,
)
from app.modules.knowledge_source.repository import KnowledgeSourceRepository

MAX_ERROR_CODE_LENGTH = 64
MAX_ERROR_MESSAGE_LENGTH = 500
RUNNING_TASK_TIMEOUT = timedelta(minutes=30)
SOURCE_FILE_MISSING = "source_file_missing"
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"(?i)(api[_ -]?key|token|password|secret)\s*[:=]\s*\S+"),
)


def sanitize_error_message(message: str) -> str:
    compact = " ".join(message.split())
    for pattern in SENSITIVE_VALUE_PATTERNS:
        compact = pattern.sub("[REDACTED]", compact)
    return compact[:MAX_ERROR_MESSAGE_LENGTH]


class DocumentService:
    def __init__(self, session: AsyncSession):
        self.repo = DocumentRepository(session)
        self.source_repo = KnowledgeSourceRepository(session)

    async def get(self, id: int) -> Document:
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"Document not found: {id}")
        await self._reconcile(entity)
        await self.source_repo.mark_opened(entity.knowledge_source_id)
        return entity

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        parse_status: ParseStatus | None = None,
        index_status: IndexStatus | None = None,
        query: str | None = None,
        research_ready: bool = False,
        previewable_only: bool = False,
        knowledge_source_id: int | None = None,
        needs_attention: bool = False,
        file_type: DocumentFileType | None = None,
        health_status: DocumentHealthStatus | None = None,
        sort_by: str = "updated_at",
        sort_order: str = "desc",
    ) -> DocumentPage:
        parse_value = parse_status.value if parse_status else None
        index_value = index_status.value if index_status else None
        normalized_query = query.strip() if query is not None else None
        if not normalized_query:
            normalized_query = None
        for entity in await self.repo.list_library_documents():
            await self._reconcile(entity)
        entities = await self.repo.list(
            offset,
            limit,
            parse_value,
            index_value,
            normalized_query,
            research_ready,
            previewable_only,
            knowledge_source_id,
            needs_attention,
            file_type.value if file_type else None,
            health_status.value if health_status else None,
            sort_by,
            sort_order,
        )
        return DocumentPage(
            items=[self._to_read(entity) for entity in entities],
            total=await self.repo.count(
                parse_value,
                index_value,
                normalized_query,
                research_ready,
                previewable_only,
                knowledge_source_id,
                needs_attention,
                file_type.value if file_type else None,
                health_status.value if health_status else None,
            ),
            offset=offset,
            limit=limit,
        )

    async def search_content(
        self,
        query: str,
        offset: int,
        limit: int,
        knowledge_source_id: int | None,
        file_type: DocumentFileType | None,
        health_status: DocumentHealthStatus | None,
        sort_by: str,
        sort_order: str,
    ) -> ContentSearchPage:
        """Search persisted parsed content and return only evidence-backed locators."""
        normalized_query = query.strip()
        if not normalized_query:
            return ContentSearchPage(items=[], total=0, offset=offset, limit=limit)
        matches = await self.repo.list_content_matches(
            normalized_query,
            offset,
            limit,
            knowledge_source_id,
            file_type.value if file_type else None,
            health_status.value if health_status else None,
            sort_by,
            sort_order,
        )
        return ContentSearchPage(
            items=[
                self._content_search_result(entity, source_name, normalized_query)
                for entity, source_name in matches
            ],
            total=await self.repo.count_content_matches(
                normalized_query,
                knowledge_source_id,
                file_type.value if file_type else None,
                health_status.value if health_status else None,
            ),
            offset=offset,
            limit=limit,
        )

    async def statistics(self) -> DocumentStatistics:
        """Return unpaged document health counts from the same domain mapping."""
        entities = await self.repo.list_library_documents()
        counts = {status: 0 for status in DocumentHealthStatus}
        for entity in entities:
            await self._reconcile(entity)
            counts[self._health_status(entity)] += 1
        return DocumentStatistics(
            total=len(entities),
            available=counts[DocumentHealthStatus.AVAILABLE],
            processing=counts[DocumentHealthStatus.PROCESSING],
            needs_attention=counts[DocumentHealthStatus.NEEDS_ATTENTION],
        )

    async def delete(self, id: int) -> None:
        entity = await self.get(id)
        await self.repo.delete(entity)

    async def retry_parse(self, id: int) -> Document:
        entity = await self.get(id)
        current = ParseStatus(entity.parse_status)
        if current == ParseStatus.PARSING:
            raise ConflictError("Document parsing is already running")
        await self._require_source_file(entity)
        if current == ParseStatus.FAILED:
            ensure_parse_transition(current, ParseStatus.PENDING)
            self._apply_transition(entity, "parse", ParseStatus.PENDING.value)
            entity.retry_count += 1
            await self.repo.save(entity)
        elif current != ParseStatus.PENDING:
            raise ConflictError(
                "Only failed or pending document parsing can be retried"
            )

        # 本地模式没有独立任务队列；重试必须在同一请求中实际调用解析器，
        # 否则 UI 会长期停在“等待解析”且用户无法判断任务是否已启动。
        await self.parse(entity.id)
        return entity

    async def repair(self, id: int) -> tuple[Document, str]:
        """Apply the only safe repair implied by the persisted document state."""
        entity = await self.get(id)
        if entity.error_code == SOURCE_FILE_MISSING:
            await self._require_source_file(entity)
            await self._reconcile(entity)
            return entity, "refresh_source"
        if entity.parse_status in {ParseStatus.FAILED.value, ParseStatus.PENDING.value}:
            return await self.retry_parse(id), "retry_parse"
        if entity.index_status in {IndexStatus.FAILED.value, IndexStatus.OUTDATED.value, IndexStatus.PENDING.value}:
            return await self.retry_index(id), "retry_index"
        raise ConflictError("Document does not require a repair action")

    async def retry_index(self, id: int) -> Document:
        entity = await self.get(id)
        current = IndexStatus(entity.index_status)
        if current == IndexStatus.INDEXING:
            raise ConflictError("Document indexing is already running")
        if current not in {
            IndexStatus.FAILED,
            IndexStatus.OUTDATED,
            IndexStatus.PENDING,
        }:
            raise ConflictError(
                "Only failed, outdated, or pending document indexing can be retried"
            )
        if entity.parse_status != ParseStatus.SUCCEEDED.value:
            raise ConflictError("Document must be parsed successfully before indexing")
        await self._require_source_file(entity)
        if current != IndexStatus.PENDING:
            ensure_index_transition(current, IndexStatus.PENDING)
            self._apply_transition(entity, "index", IndexStatus.PENDING.value)
            entity.retry_count += 1
        return await self.repo.save(entity)

    async def delete_index(self, id: int) -> Document:
        entity = await self.get(id)
        current = IndexStatus(entity.index_status)
        if current == IndexStatus.INDEXING:
            raise ConflictError("Cannot delete an index while indexing is running")
        if current != IndexStatus.PENDING:
            ensure_index_transition(current, IndexStatus.PENDING)
            self._apply_transition(entity, "index", IndexStatus.PENDING.value)
        return await self.repo.save(entity)

    async def parse(self, id: int) -> ParsedContentSummary:
        entity = await self.get(id)
        current = ParseStatus(entity.parse_status)
        if current == ParseStatus.PARSING:
            raise ConflictError("Document parsing is already running")
        if current != ParseStatus.PENDING:
            raise ConflictError("Only pending documents can be parsed")
        path = await self._source_file_path(entity)
        await self.mark_parse_status(entity, ParseStatus.PARSING)
        try:
            parser = create_parser(path)
            parsed = await asyncio.to_thread(parser.parse, path)
        except DocumentParserError as exc:
            await self.mark_parse_status(entity, ParseStatus.FAILED, exc.code, str(exc))
            raise ConflictError(str(exc)) from exc
        except OSError as exc:
            await self.mark_parse_status(
                entity,
                ParseStatus.FAILED,
                "document_unavailable",
                "Document could not be read during parsing",
            )
            raise ConflictError("Document could not be read during parsing") from exc
        except Exception as exc:
            await self.mark_parse_status(
                entity,
                ParseStatus.FAILED,
                "document_parse_failed",
                "Document parsing failed",
            )
            raise ConflictError("Document parsing failed") from exc
        entity.parsed_title = parsed.title
        entity.parsed_content = parsed.model_dump_json()
        entity.parsed_is_scanned = parsed.is_scanned
        entity.parsed_page_count = len(parsed.pages)
        entity.index_status = IndexStatus.OUTDATED.value
        await self.mark_parse_status(entity, ParseStatus.SUCCEEDED)
        return self._content_summary(entity, parsed)

    async def content_summary(self, id: int) -> ParsedContentSummary:
        entity = await self.get(id)
        if (
            not entity.parsed_content
            or entity.parse_status != ParseStatus.SUCCEEDED.value
        ):
            raise ConflictError("Document has no successful parsed content")
        try:
            parsed = ParsedDocument.model_validate_json(entity.parsed_content)
        except ValueError as exc:
            raise ConflictError("Stored parsed content is invalid") from exc
        return self._content_summary(entity, parsed)

    async def mark_parse_status(
        self,
        entity: Document,
        target: ParseStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> Document:
        ensure_parse_transition(ParseStatus(entity.parse_status), target)
        self._apply_transition(entity, "parse", target.value, error_code, error_message)
        return await self.repo.save(entity)

    async def mark_index_status(
        self,
        entity: Document,
        target: IndexStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> Document:
        ensure_index_transition(IndexStatus(entity.index_status), target)
        self._apply_transition(entity, "index", target.value, error_code, error_message)
        return await self.repo.save(entity)

    async def _reconcile(self, entity: Document) -> None:
        now = datetime.now(UTC)
        started_at = entity.started_at
        if started_at is not None and started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        is_stale = started_at is not None and now - started_at > RUNNING_TASK_TIMEOUT
        if is_stale and entity.parse_status == ParseStatus.PARSING.value:
            self._apply_transition(
                entity,
                "parse",
                ParseStatus.FAILED.value,
                "task_stalled",
                "Parse task stopped without reporting completion",
            )
            await self.repo.save(entity)
        elif is_stale and entity.index_status == IndexStatus.INDEXING.value:
            self._apply_transition(
                entity,
                "index",
                IndexStatus.FAILED.value,
                "task_stalled",
                "Index task stopped without reporting completion",
            )
            await self.repo.save(entity)
        await self._mark_missing_file(entity)

    async def _mark_missing_file(self, entity: Document) -> None:
        source = await self.source_repo.get(entity.knowledge_source_id)
        if source is None:
            return
        path = Path(source.root_path) / entity.file_path
        try:
            exists = path.is_file()
        except OSError:
            return
        if exists:
            if entity.error_code == SOURCE_FILE_MISSING:
                # 文件短暂不可用后重新出现时，旧失败状态不能永久阻塞重试或同步。
                self._apply_transition(entity, "parse", ParseStatus.PENDING.value)
                entity.index_status = IndexStatus.OUTDATED.value
                await self.repo.save(entity)
            return
        if entity.error_code == SOURCE_FILE_MISSING:
            return
        entity.parse_status = ParseStatus.FAILED.value
        entity.index_status = IndexStatus.OUTDATED.value
        entity.error_code = SOURCE_FILE_MISSING
        entity.error_message = "The source file is no longer available"
        entity.finished_at = datetime.now(UTC)
        logger.warning(
            "document_state_changed id=%s reason=source_file_missing", entity.id
        )
        await self.repo.save(entity)

    async def _require_source_file(self, entity: Document) -> None:
        await self._source_file_path(entity)

    async def _source_file_path(self, entity: Document) -> Path:
        source = await self.source_repo.get(entity.knowledge_source_id)
        if source is None:
            raise ConflictError("Document source file is not available")
        path = Path(source.root_path) / entity.file_path
        try:
            available = path.is_file()
        except OSError:
            available = False
        if not available:
            raise ConflictError("Document source file is not available")
        return path

    @staticmethod
    def _file_type(entity: Document) -> DocumentFileType:
        name = entity.original_filename or entity.file_path
        suffix = Path(name).suffix.lower().lstrip(".")
        return DocumentFileType(suffix) if suffix in DocumentFileType._value2member_map_ else DocumentFileType.OTHER

    @classmethod
    def _content_search_result(
        cls, entity: Document, source_name: str, query: str
    ) -> ContentSearchResult:
        """Build a locator from parser output; unknown is safer than an invented page."""
        try:
            parsed = ParsedDocument.model_validate_json(entity.parsed_content or "")
        except ValueError:
            return ContentSearchResult(
                document_id=entity.id,
                document_name=entity.original_filename or entity.file_path,
                knowledge_source_id=entity.knowledge_source_id,
                source_name=source_name,
                locator_type=ContentLocatorType.UNKNOWN,
                snippet="解析内容格式无效，无法提供定位摘录。",
            )

        needle = query.casefold()
        for page in parsed.pages:
            if needle in page.text.casefold():
                locator_type = (
                    ContentLocatorType.SLIDE
                    if cls._file_type(entity) == DocumentFileType.PPTX
                    else ContentLocatorType.PAGE
                )
                unit = "张幻灯片" if locator_type == ContentLocatorType.SLIDE else "页"
                return ContentSearchResult(
                    document_id=entity.id,
                    document_name=entity.original_filename or entity.file_path,
                    knowledge_source_id=entity.knowledge_source_id,
                    source_name=source_name,
                    locator_type=locator_type,
                    locator=f"第 {page.page_number} {unit}",
                    snippet=cls._excerpt(page.text, query),
                )
        for section in parsed.sections:
            if needle in section.text.casefold():
                return ContentSearchResult(
                    document_id=entity.id,
                    document_name=entity.original_filename or entity.file_path,
                    knowledge_source_id=entity.knowledge_source_id,
                    source_name=source_name,
                    locator_type=ContentLocatorType.SECTION,
                    locator=f"章节：{section.heading}",
                    snippet=cls._excerpt(section.text, query),
                )
        return ContentSearchResult(
            document_id=entity.id,
            document_name=entity.original_filename or entity.file_path,
            knowledge_source_id=entity.knowledge_source_id,
            source_name=source_name,
            locator_type=ContentLocatorType.UNKNOWN,
            snippet=cls._excerpt(parsed.text, query),
        )

    @staticmethod
    def _excerpt(text: str, query: str, radius: int = 96) -> str:
        """Return a bounded plain-text excerpt without interpreting it as HTML."""
        position = text.casefold().find(query.casefold())
        if position < 0:
            return "定位信息不可用"
        start = max(0, position - radius)
        end = min(len(text), position + len(query) + radius)
        prefix = "…" if start else ""
        suffix = "…" if end < len(text) else ""
        return f"{prefix}{' '.join(text[start:end].split())}{suffix}"

    @staticmethod
    def _health_status(entity: Document) -> DocumentHealthStatus:
        source_unavailable = entity.source is not None and entity.source.sync_status == "unavailable"
        if entity.parse_status == ParseStatus.FAILED.value or entity.index_status in {IndexStatus.FAILED.value, IndexStatus.OUTDATED.value} or entity.error_code == SOURCE_FILE_MISSING or source_unavailable:
            return DocumentHealthStatus.NEEDS_ATTENTION
        if entity.parse_status == ParseStatus.SUCCEEDED.value and entity.index_status == IndexStatus.SUCCEEDED.value:
            return DocumentHealthStatus.AVAILABLE
        return DocumentHealthStatus.PROCESSING

    def _to_read(self, entity: Document) -> DocumentRead:
        health = self._health_status(entity)
        actions = ["view"] if health == DocumentHealthStatus.AVAILABLE else (["repair", "view"] if health == DocumentHealthStatus.NEEDS_ATTENTION else ["view"])
        reason = entity.error_message if health == DocumentHealthStatus.NEEDS_ATTENTION else ("内容处理已完成" if health == DocumentHealthStatus.AVAILABLE else "正在处理文档")
        file_type = self._file_type(entity)
        return DocumentRead.model_validate(entity).model_copy(update={"file_type": file_type, "extension": Path(entity.original_filename or entity.file_path).suffix.lower().lstrip(".") or None, "preview_capability": file_type == DocumentFileType.PDF, "health_status": health, "health_reason": reason, "available_actions": actions, "progress": None, "task_id": None})

    @staticmethod
    def _content_summary(
        entity: Document, parsed: ParsedDocument
    ) -> ParsedContentSummary:
        return ParsedContentSummary(
            document_id=entity.id,
            title=parsed.title,
            page_count=len(parsed.pages),
            page_numbers=[page.page_number for page in parsed.pages],
            section_headings=[section.heading for section in parsed.sections],
            yaml_metadata=parsed.yaml_metadata,
            is_scanned=parsed.is_scanned,
            character_count=len(parsed.text),
        )

    @staticmethod
    def _apply_transition(
        entity: Document,
        task: str,
        target: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        previous = entity.parse_status if task == "parse" else entity.index_status
        if task == "parse":
            entity.parse_status = target
        else:
            entity.index_status = target
        now = datetime.now(UTC)
        if target in {ParseStatus.PARSING.value, IndexStatus.INDEXING.value}:
            entity.started_at = now
            entity.finished_at = None
        elif target == "pending":
            entity.started_at = None
            entity.finished_at = None
        else:
            entity.finished_at = now
        if target == "failed":
            entity.error_code = (error_code or "task_failed")[:MAX_ERROR_CODE_LENGTH]
            entity.error_message = sanitize_error_message(
                error_message or "Task failed"
            )
        else:
            entity.error_code = None
            entity.error_message = None
        logger.info(
            "document_state_changed id=%s task=%s from=%s to=%s",
            entity.id,
            task,
            previous,
            target,
        )
