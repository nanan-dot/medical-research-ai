"""Document status, retry, and stale-task management."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.common.logger import logger
from app.modules.document.model import Document
from app.modules.document.parsers.base import DocumentParserError
from app.modules.document.parsers.factory import create_parser
from app.modules.document.parsers.schemas import ParsedContentSummary, ParsedDocument
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import (
    DocumentPage,
    DocumentRead,
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
        return entity

    async def list(
        self,
        offset: int = 0,
        limit: int = 20,
        parse_status: ParseStatus | None = None,
        index_status: IndexStatus | None = None,
    ) -> DocumentPage:
        parse_value = parse_status.value if parse_status else None
        index_value = index_status.value if index_status else None
        for entity in await self.repo.list_all():
            await self._reconcile(entity)
        entities = await self.repo.list(offset, limit, parse_value, index_value)
        return DocumentPage(
            items=[DocumentRead.model_validate(entity) for entity in entities],
            total=await self.repo.count(parse_value, index_value),
            offset=offset,
            limit=limit,
        )

    async def delete(self, id: int) -> None:
        entity = await self.get(id)
        await self.repo.delete(entity)

    async def retry_parse(self, id: int) -> Document:
        entity = await self.get(id)
        current = ParseStatus(entity.parse_status)
        if current == ParseStatus.PARSING:
            raise ConflictError("Document parsing is already running")
        if current != ParseStatus.FAILED:
            raise ConflictError("Only failed document parsing can be retried")
        await self._require_source_file(entity)
        ensure_parse_transition(current, ParseStatus.PENDING)
        self._apply_transition(entity, "parse", ParseStatus.PENDING.value)
        entity.retry_count += 1
        return await self.repo.save(entity)

    async def retry_index(self, id: int) -> Document:
        entity = await self.get(id)
        current = IndexStatus(entity.index_status)
        if current == IndexStatus.INDEXING:
            raise ConflictError("Document indexing is already running")
        if current not in {IndexStatus.FAILED, IndexStatus.OUTDATED}:
            raise ConflictError(
                "Only failed or outdated document indexing can be retried"
            )
        if entity.parse_status != ParseStatus.SUCCEEDED.value:
            raise ConflictError("Document must be parsed successfully before indexing")
        await self._require_source_file(entity)
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
        if exists or entity.error_code == "source_file_missing":
            return
        entity.parse_status = ParseStatus.FAILED.value
        entity.index_status = IndexStatus.OUTDATED.value
        entity.error_code = "source_file_missing"
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
