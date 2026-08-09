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
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
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

    async def list(self, offset: int = 0, limit: int = 20) -> list[KnowledgeSource]:
        entities = await self.repo.list(offset=offset, limit=limit)
        for entity in entities:
            await self._refresh_availability(entity)
        return entities

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
