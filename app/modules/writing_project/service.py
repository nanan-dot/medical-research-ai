"""写作项目业务编排：材料隔离、乐观并发与不可变快照。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.writing_project.model import (
    WritingGeneratedContent,
    WritingProject,
    WritingUserMaterial,
    WritingVersion,
)
from app.modules.writing_project.repository import WritingProjectRepository
from app.modules.writing_project.schema import (
    GeneratedContent,
    UserMaterialCreate,
    UserMaterialRead,
    WritingProjectCreate,
    WritingProjectRead,
    WritingProjectSnapshot,
    WritingProjectUpdate,
    WritingType,
    WritingVersionRead,
)
from app.modules.writing_project.versioning import restore_snapshot, snapshot_content


class WritingProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WritingProjectRepository(session)

    async def create(self, payload: WritingProjectCreate) -> WritingProjectRead:
        entity = WritingProject(
            name=payload.name,
            writing_type=payload.writing_type,
            confidential=payload.confidential,
            generated_content=WritingGeneratedContent(
                content_json=self._dump(payload.generated_content)
            ),
        )
        return self._read(await self.repository.create(entity))

    async def get(self, project_id: int) -> WritingProjectRead:
        return self._read(await self._require(project_id))

    async def list_projects(self) -> list[WritingProjectRead]:
        return [self._read(entity) for entity in await self.repository.list_projects()]

    async def update(
        self,
        project_id: int,
        payload: WritingProjectUpdate,
    ) -> WritingProjectRead:
        entity = await self._require(project_id)
        values: dict[str, object] = {
            "version": payload.expected_version + 1,
            "updated_at": datetime.now(UTC),
        }
        if payload.name is not None:
            values["name"] = payload.name
        if payload.confidential is not None:
            values["confidential"] = payload.confidential
        if payload.generated_content is not None:
            entity.generated_content.content_json = self._dump(
                payload.generated_content
            )
        if not await self.repository.update_if_version(
            project_id, payload.expected_version, values
        ):
            raise ConflictError("Writing project version conflict; reload and retry")
        await self.session.refresh(entity)
        return self._read(entity)

    async def add_material(
        self,
        project_id: int,
        payload: UserMaterialCreate,
    ) -> UserMaterialRead:
        project = await self._require(project_id)
        material = await self.repository.add_material(
            WritingUserMaterial(project_id=project.id, **payload.model_dump())
        )
        await self.session.refresh(project, attribute_names=["materials"])
        return UserMaterialRead.model_validate(material)

    async def save_version(
        self, project_id: int, *, expected_version: int
    ) -> WritingVersionRead:
        entity = await self._require(project_id)
        self._check_version(entity, expected_version)
        prior_versions = await self.repository.list_versions(project_id)
        next_snapshot_version = (
            max((item.version for item in prior_versions), default=0) + 1
        )
        snapshot = snapshot_content(
            self._content(entity),
            version=next_snapshot_version,
            parent_version=prior_versions[-1].version if prior_versions else None,
        )
        stored = await self.repository.add_version(
            WritingVersion(
                project_id=project_id,
                version=snapshot.version,
                parent_version=snapshot.parent_version,
                content_json=self._dump(snapshot.content),
            )
        )
        return self._read_version(stored)

    async def list_versions(self, project_id: int) -> list[WritingVersionRead]:
        await self._require(project_id)
        return [
            self._read_version(item)
            for item in await self.repository.list_versions(project_id)
        ]

    async def restore_version(
        self,
        project_id: int,
        version: int,
        *,
        expected_version: int,
    ) -> WritingProjectRead:
        entity = await self._require(project_id)
        self._check_version(entity, expected_version)
        stored = await self.repository.get_version(project_id, version)
        if stored is None:
            raise NotFoundError("Writing project version not found")
        source = WritingProjectSnapshot(
            version=stored.version,
            parent_version=stored.parent_version,
            content=GeneratedContent.model_validate_json(stored.content_json),
        )
        restored = restore_snapshot(source, next_version=entity.version + 1)
        entity.generated_content.content_json = self._dump(restored.content)
        if not await self.repository.update_if_version(
            project_id,
            expected_version,
            {"version": restored.version, "updated_at": datetime.now(UTC)},
        ):
            raise ConflictError("Writing project version conflict; reload and retry")
        await self.repository.add_version(
            WritingVersion(
                project_id=project_id,
                version=restored.version,
                parent_version=restored.parent_version,
                content_json=self._dump(restored.content),
            )
        )
        await self.session.refresh(entity)
        return self._read(entity)

    async def delete(self, project_id: int) -> None:
        await self.repository.delete(await self._require(project_id))

    async def _require(self, project_id: int) -> WritingProject:
        entity = await self.repository.get(project_id)
        if entity is None:
            raise NotFoundError("Writing project not found")
        return entity

    @staticmethod
    def _check_version(entity: WritingProject, expected_version: int) -> None:
        if entity.version != expected_version:
            raise ConflictError("Writing project version conflict; reload and retry")

    @staticmethod
    def _dump(content: GeneratedContent) -> str:
        return json.dumps(content.model_dump(mode="json"), ensure_ascii=False)

    @staticmethod
    def _content(entity: WritingProject) -> GeneratedContent:
        return GeneratedContent.model_validate_json(
            entity.generated_content.content_json
        )

    @classmethod
    def _read(cls, entity: WritingProject) -> WritingProjectRead:
        return WritingProjectRead(
            id=entity.id,
            name=entity.name,
            writing_type=cast(WritingType, entity.writing_type),
            confidential=entity.confidential,
            generated_content=cls._content(entity),
            version=entity.version,
            user_materials=[
                UserMaterialRead.model_validate(item) for item in entity.materials
            ],
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @classmethod
    def _read_version(cls, entity: WritingVersion) -> WritingVersionRead:
        return WritingVersionRead(
            version=entity.version,
            parent_version=entity.parent_version,
            content=GeneratedContent.model_validate_json(entity.content_json),
            created_at=entity.created_at,
        )
