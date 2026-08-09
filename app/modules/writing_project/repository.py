"""写作项目数据库访问层。"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.writing_project.model import (
    WritingProject,
    WritingUserMaterial,
    WritingVersion,
)


class WritingProjectRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entity: WritingProject) -> WritingProject:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get(self, project_id: int) -> WritingProject | None:
        return await self.session.get(WritingProject, project_id)

    async def list_projects(self) -> list[WritingProject]:
        result = await self.session.execute(
            select(WritingProject).order_by(WritingProject.id.desc())
        )
        return list(result.scalars())

    async def save(self, entity: WritingProject) -> WritingProject:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update_if_version(
        self, project_id: int, expected_version: int, values: dict[str, object]
    ) -> bool:
        result = await self.session.execute(
            update(WritingProject)
            .where(
                WritingProject.id == project_id,
                WritingProject.version == expected_version,
            )
            .values(**values)
        )
        await self.session.flush()
        return bool(getattr(result, "rowcount", 0) == 1)

    async def delete(self, entity: WritingProject) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    async def add_material(self, entity: WritingUserMaterial) -> WritingUserMaterial:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def add_version(self, entity: WritingVersion) -> WritingVersion:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_version(self, project_id: int, version: int) -> WritingVersion | None:
        result = await self.session.execute(
            select(WritingVersion).where(
                WritingVersion.project_id == project_id,
                WritingVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(self, project_id: int) -> list[WritingVersion]:
        result = await self.session.execute(
            select(WritingVersion)
            .where(WritingVersion.project_id == project_id)
            .order_by(WritingVersion.version)
        )
        return list(result.scalars())
