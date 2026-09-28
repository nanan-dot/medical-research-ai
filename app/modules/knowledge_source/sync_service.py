"""Incremental synchronization between an authorized directory and document records."""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError
from app.common.hashing import sha256_file
from app.modules.document.model import Document
from app.modules.document.repository import DocumentRepository
from app.modules.document.schema import DocumentScanState, IndexStatus, ParseStatus
from app.modules.document.service import SOURCE_FILE_MISSING, DocumentService
from app.modules.document_relocation.file_versions import FileVersionService
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.scanner import scan_directory
from app.modules.knowledge_source.schema import (
    KnowledgeSourceSyncStatus,
    KnowledgeSourceSyncSummary,
)
from app.modules.knowledge_source.service import KnowledgeSourceService
from app.modules.knowledge_source.sync_progress import (
    SyncPhase,
    SyncProgress,
    calculate_progress,
)

logger = logging.getLogger(__name__)

SyncProgressReporter = Callable[[SyncProgress], Awaitable[None]]


class KnowledgeSourceSyncService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.source_service = KnowledgeSourceService(session)
        self.document_repo = DocumentRepository(session)

    async def sync(
        self,
        source_id: int,
        progress_reporter: SyncProgressReporter | None = None,
    ) -> KnowledgeSourceSyncSummary:
        source = await self.source_service.get(source_id)
        if not source.enabled:
            raise ConflictError("Disabled knowledge source cannot be synchronized")
        if source.sync_status == KnowledgeSourceSyncStatus.SCANNING.value:
            raise ConflictError("Knowledge source synchronization is already running")

        source.sync_status = KnowledgeSourceSyncStatus.SCANNING.value
        source.error_message = None
        await self.source_service.repo.save(source)

        await self._report(
            progress_reporter,
            calculate_progress(SyncPhase.SCANNING, 0, None),
        )
        scan = await asyncio.to_thread(scan_directory, Path(source.root_path))
        existing = {
            document.normalized_file_path: document
            for document in await self.document_repo.list_by_source(source.id)
        }
        counts = {
            "added": 0,
            "modified": 0,
            "deleted": 0,
            "skipped": scan.skipped_duplicates,
            "failed": scan.failures,
        }
        documents_to_parse: list[int] = []
        completed_units = 0

        for path_key, scanned in scan.files.items():
            document = existing.pop(path_key, None)
            if (
                document is not None
                and document.file_size == scanned.file_size
                and document.modified_time_ns == scanned.modified_time_ns
            ):
                if document.error_code == SOURCE_FILE_MISSING:
                    # 扫描结果证明文件已恢复可读；重新解析而不是永久保留旧缺失错误。
                    document.parse_status = ParseStatus.PENDING.value
                    document.index_status = IndexStatus.OUTDATED.value
                    document.error_code = None
                    document.error_message = None
                    document.started_at = None
                    document.finished_at = None
                    await self.document_repo.save(document)
                    documents_to_parse.append(document.id)
                    counts["modified"] += 1
                    completed_units += 1
                    continue
                if document.parse_status == ParseStatus.PENDING.value:
                    # 手动重试此前仅改为 pending 的文档也要由同步真正执行解析。
                    documents_to_parse.append(document.id)
                    counts["modified"] += 1
                    completed_units += 1
                    continue
                counts["skipped"] += 1
                completed_units += 1
                continue
            try:
                file_hash = await asyncio.to_thread(sha256_file, scanned.path)
            except OSError:
                counts["failed"] += 1
                continue

            modified_time = datetime.fromtimestamp(
                scanned.modified_time_ns / 1_000_000_000, UTC
            )
            if document is None:
                created = await self.document_repo.create(
                    Document(
                        knowledge_source_id=source.id,
                        file_path=scanned.relative_path,
                        normalized_file_path=path_key,
                        file_hash=file_hash,
                        file_size=scanned.file_size,
                        modified_time=modified_time,
                        modified_time_ns=scanned.modified_time_ns,
                        scan_state=DocumentScanState.PENDING.value,
                        parse_status=ParseStatus.PENDING.value,
                        index_status=IndexStatus.PENDING.value,
                    )
                )
                documents_to_parse.append(created.id)
                await FileVersionService(self.session).observe(created)
                counts["added"] += 1
            elif document.file_hash == file_hash:
                document.file_size = scanned.file_size
                document.modified_time = modified_time
                document.modified_time_ns = scanned.modified_time_ns
                await self.document_repo.save(document)
                counts["skipped"] += 1
            else:
                document.file_path = scanned.relative_path
                document.file_hash = file_hash
                document.file_size = scanned.file_size
                document.modified_time = modified_time
                document.modified_time_ns = scanned.modified_time_ns
                document.scan_state = DocumentScanState.OUTDATED.value
                document.parse_status = ParseStatus.PENDING.value
                document.index_status = IndexStatus.OUTDATED.value
                document.error_code = None
                document.error_message = None
                document.started_at = None
                document.finished_at = None
                await self.document_repo.save(document)
                await FileVersionService(self.session).observe(document)
                counts["modified"] += 1
                documents_to_parse.append(document.id)
            completed_units += 1

        for path_key, document in existing.items():
            belongs_to_failed_directory = any(
                not prefix
                or prefix == "."
                or path_key == prefix
                or path_key.startswith(prefix + os.sep)
                for prefix in scan.failed_prefixes
            )
            if path_key in scan.failed_paths or belongs_to_failed_directory:
                continue
            await self.document_repo.delete(document)
            counts["deleted"] += 1

        source.last_sync_time = datetime.now(UTC)
        source.sync_added = counts["added"]
        source.sync_modified = counts["modified"]
        source.sync_deleted = counts["deleted"]
        source.sync_skipped = counts["skipped"]
        source.sync_failed = counts["failed"]
        if counts["failed"]:
            source.sync_status = KnowledgeSourceSyncStatus.COMPLETED_WITH_ERRORS.value
            source.error_message = (
                f"{counts['failed']} file system entries could not be scanned"
            )
        else:
            source.sync_status = KnowledgeSourceSyncStatus.COMPLETED.value
            source.error_message = None
        await self.source_service.repo.save(source)
        # 新旧记录必须先提交，解析器才能在独立处理阶段读取完整来源与文档状态。
        # 顺序执行避免在同一个 AsyncSession 上并发 SQL 操作；单项失败由 parse() 落库，
        # 不影响其余文件，也不计入同步 failed（failed 仅代表扫描/文件系统层失败，
        # 解析失败体现在文档 parse_status=failed，由文档库与知识库 stats 呈现）。
        await self.session.commit()
        total_work_units = completed_units + len(documents_to_parse)
        await self._report(
            progress_reporter,
            calculate_progress(
                SyncPhase.PERSISTING,
                completed_units,
                total_work_units,
            ),
        )
        parser = DocumentService(self.session)
        for parse_index, document_id in enumerate(documents_to_parse, start=1):
            document = await self.document_repo.get(document_id)
            await self._report(
                progress_reporter,
                calculate_progress(
                    SyncPhase.PARSING,
                    completed_units + parse_index - 1,
                    total_work_units,
                    Path(document.file_path).name if document is not None else None,
                ),
            )
            try:
                await parser.parse(document_id)
            except ConflictError:
                # parse() 会把解析器错误转换为 ConflictError，同时先把失败详情落库。
                # 重复触发导致的 pending/parsing 前置校验不是文件解析失败，忽略。
                pass
            except Exception:
                # 非预期基础设施异常不应让同批文件停止；记录完整堆栈供运维排查。
                logger.exception(
                    "knowledge_source_parse_unexpected_error document_id=%s",
                    document_id,
                )

        await self._report(
            progress_reporter,
            calculate_progress(
                SyncPhase.FINALIZING,
                completed_units + len(documents_to_parse),
                total_work_units,
            ),
        )

        return self._summary(await self.source_service.get(source_id))

    @staticmethod
    async def _report(
        progress_reporter: SyncProgressReporter | None,
        progress: SyncProgress,
    ) -> None:
        if progress_reporter is not None:
            await progress_reporter(progress)

    async def status(self, source_id: int) -> KnowledgeSourceSyncSummary:
        return self._summary(await self.source_service.get(source_id))

    @staticmethod
    def _summary(source: KnowledgeSource) -> KnowledgeSourceSyncSummary:
        return KnowledgeSourceSyncSummary(
            knowledge_source_id=source.id,
            sync_status=KnowledgeSourceSyncStatus(source.sync_status),
            last_sync_time=source.last_sync_time,
            added=source.sync_added,
            modified=source.sync_modified,
            deleted=source.sync_deleted,
            skipped=source.sync_skipped,
            failed=source.sync_failed,
            error_message=source.error_message,
        )
