"""Knowledge-source authorization and lifecycle rules."""

import os
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    ConflictError,
    InvalidPathError,
    NotFoundError,
    PermissionDeniedError,
    TemporarilyUnavailableError,
)
from app.modules.knowledge_source.health import health_status
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.repository import (
    KnowledgeSourceRepository,
    KnowledgeSourceStatsRecord,
)
from app.modules.knowledge_source.schema import (
    KnowledgeBaseIssueBreakdown,
    KnowledgeBaseSummary,
    KnowledgeSourceCreate,
    KnowledgeSourceHealthStatus,
    KnowledgeSourcePage,
    KnowledgeSourceRead,
    KnowledgeSourceStats,
    KnowledgeSourceSyncStatus,
    KnowledgeSourceUpdate,
)


class KnowledgeSourcePathError(ValueError):
    """A path is invalid without exposing its contents."""


def normalize_authorized_directory(raw_path: str) -> tuple[str, str]:
    """Resolve links and return display/canonical keys without reading directory contents."""
    candidate = Path(raw_path).expanduser()
    try:
        resolved = candidate.resolve(strict=True)
        if not resolved.is_dir():
            raise KnowledgeSourcePathError("Knowledge source path is not a directory")
        if not os.access(resolved, os.R_OK | os.X_OK):
            raise PermissionDeniedError("Knowledge source directory is not readable")
        with os.scandir(resolved):
            pass
    except PermissionDeniedError:
        raise
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise KnowledgeSourcePathError(
            "Knowledge source directory does not exist"
        ) from exc
    except PermissionError as exc:
        raise PermissionDeniedError(
            "Knowledge source directory is not readable"
        ) from exc
    except OSError as exc:
        raise TemporarilyUnavailableError(
            "Knowledge source directory is temporarily unavailable"
        ) from exc

    display_path = str(resolved)
    canonical_path = os.path.normcase(os.path.normpath(display_path))
    return display_path, canonical_path


class KnowledgeSourceService:
    def __init__(self, session: AsyncSession):
        self.repo = KnowledgeSourceRepository(session)

    async def get(self, id: int) -> KnowledgeSource:
        entity = await self.repo.get(id)
        if not entity:
            raise NotFoundError(f"KnowledgeSource not found: {id}")
        await self._refresh_availability(entity)
        return entity

    async def list(self, offset: int = 0, limit: int = 20) -> list[KnowledgeSourceRead]:
        entities = await self.repo.list(offset=offset, limit=limit)
        for entity in entities:
            await self._refresh_availability(entity)
        stats_by_source_id = await self.repo.stats_by_source_ids(
            [entity.id for entity in entities]
        )
        return [
            self._read(
                entity,
                self._stats_from_record(stats_by_source_id.get(entity.id)),
            )
            for entity in entities
        ]

    async def page(
        self,
        q: str | None,
        source_type: str | None,
        health_status: str | None,
        enabled: bool | None,
        auto_sync: bool | None,
        is_pinned: bool | None,
        sort_by: str,
        sort_order: str,
        offset: int,
        limit: int,
    ) -> KnowledgeSourcePage:
        entities, total = await self.repo.page(
            q,
            source_type,
            health_status,
            enabled,
            auto_sync,
            is_pinned,
            sort_by,
            sort_order,
            offset,
            limit,
        )
        stats = await self.repo.stats_by_source_ids([entity.id for entity in entities])
        return KnowledgeSourcePage(
            items=[
                self._read(entity, self._stats_from_record(stats.get(entity.id)))
                for entity in entities
            ],
            total=total,
            offset=offset,
            limit=limit,
        )

    async def summary(self) -> KnowledgeBaseSummary:
        """Return an unpaged, SQL-derived summary of supported source types."""
        values = await self.repo.summary()
        total = values["total_item_count"]
        issue_breakdown = KnowledgeBaseIssueBreakdown(
            **{
                name: values.pop(name)
                for name in KnowledgeBaseIssueBreakdown.model_fields
            }
        )
        return KnowledgeBaseSummary(
            **values,
            issue_breakdown=issue_breakdown,
            availability_percent=(
                None
                if total == 0
                else round(values["available_item_count"] * 100 / total, 2)
            ),
        )

    async def read(self, id: int) -> KnowledgeSourceRead:
        entity = await self.get(id)
        return await self._read_with_stats(entity)

    async def stats(self, id: int) -> KnowledgeSourceStats:
        entity = await self.get(id)
        return await self._stats_for_entity(entity)

    async def create(self, data: KnowledgeSourceCreate) -> KnowledgeSource:
        try:
            root_path, normalized_path = normalize_authorized_directory(data.root_path)
        except KnowledgeSourcePathError as exc:
            raise InvalidPathError(str(exc)) from exc
        if await self.repo.get_by_normalized_path(normalized_path):
            raise ConflictError("Knowledge source directory is already registered")
        entity = KnowledgeSource(
            name=data.name.strip(),
            source_type=data.source_type.value,
            root_path=root_path,
            normalized_root_path=normalized_path,
            enabled=data.enabled,
            sync_status=KnowledgeSourceSyncStatus.IDLE.value,
        )
        return await self.repo.create(entity)

    async def update(self, id: int, data: KnowledgeSourceUpdate) -> KnowledgeSource:
        entity = await self.get(id)
        if data.name is not None:
            entity.name = data.name.strip()
        if data.enabled is not None:
            entity.enabled = data.enabled
        if data.auto_sync is not None:
            entity.auto_sync = data.auto_sync
        if data.is_pinned is not None:
            entity.is_pinned = data.is_pinned
        return await self.repo.save(entity)

    async def delete(self, id: int) -> None:
        entity = await self.get(id)
        await self.repo.delete(entity)

    async def _refresh_availability(self, entity: KnowledgeSource) -> None:
        if entity.normalized_root_path.startswith("legacy:"):
            return
        try:
            normalize_authorized_directory(entity.root_path)
        except (
            KnowledgeSourcePathError,
            PermissionDeniedError,
            TemporarilyUnavailableError,
        ) as exc:
            entity.sync_status = KnowledgeSourceSyncStatus.UNAVAILABLE.value
            entity.error_message = str(exc)
            await self.repo.save(entity)
        else:
            if entity.sync_status == KnowledgeSourceSyncStatus.UNAVAILABLE.value:
                entity.sync_status = KnowledgeSourceSyncStatus.IDLE.value
                entity.error_message = None
                await self.repo.save(entity)

    async def _read_with_stats(self, entity: KnowledgeSource) -> KnowledgeSourceRead:
        return self._read(entity, await self._stats_for_entity(entity))

    async def _stats_for_entity(self, entity: KnowledgeSource) -> KnowledgeSourceStats:
        stats_by_source_id = await self.repo.stats_by_source_ids([entity.id])
        return self._stats_from_record(stats_by_source_id.get(entity.id))

    @staticmethod
    def _read(
        entity: KnowledgeSource, stats: KnowledgeSourceStats
    ) -> KnowledgeSourceRead:
        return KnowledgeSourceRead.model_validate(entity).model_copy(
            update={
                "stats": stats,
                "health_status": KnowledgeSourceHealthStatus(
                    health_status(
                        entity.enabled,
                        entity.sync_status,
                        stats.failed,
                        entity.sync_status
                        == KnowledgeSourceSyncStatus.COMPLETED_WITH_ERRORS.value,
                    )
                ),
            }
        )

    @staticmethod
    def _stats_from_record(
        stats_record: KnowledgeSourceStatsRecord | None,
    ) -> KnowledgeSourceStats:
        if stats_record is None:
            return KnowledgeSourceStats()
        availability_percent = (
            None
            if stats_record.total_files == 0
            else round(stats_record.available * 100 / stats_record.total_files, 2)
        )
        return KnowledgeSourceStats(
            total_files=stats_record.total_files,
            parsed=stats_record.parsed,
            indexed=stats_record.indexed,
            pending=stats_record.pending,
            failed=stats_record.failed,
            available=stats_record.available,
            processing=stats_record.processing,
            needs_attention=stats_record.needs_attention,
            availability_percent=availability_percent,
        )
