"""AI 使用记录数据库访问与披露草稿编排。"""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.ai_disclosure.disclosure_draft import build_disclosure_draft
from app.modules.ai_disclosure.model import AIUsageEvent, DisclosureDraft
from app.modules.ai_disclosure.schema import (
    AIUsageEventCreate,
    AIUsageEventRead,
    DisclosureDraftRead,
)
from app.modules.writing_project.model import WritingProject


class AIDisclosureService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_event(self, project_id: int, payload: AIUsageEventCreate) -> AIUsageEventRead:
        await self._require_project(project_id)
        entity = AIUsageEvent(project_id=project_id, event_id=uuid4().hex, **payload.model_dump())
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return AIUsageEventRead.model_validate(entity)

    async def list_events(self, project_id: int) -> list[AIUsageEventRead]:
        await self._require_project(project_id)
        result = await self.session.execute(
            select(AIUsageEvent).where(AIUsageEvent.project_id == project_id).order_by(AIUsageEvent.id)
        )
        return [AIUsageEventRead.model_validate(item) for item in result.scalars()]

    async def get_or_create_draft(self, project_id: int) -> DisclosureDraftRead:
        project = await self._require_project(project_id)
        events = await self.list_events(project_id)
        result = await self.session.execute(
            select(DisclosureDraft).where(DisclosureDraft.project_id == project_id)
        )
        entity = result.scalar_one_or_none()
        confidential = "confidential" in project.name.lower()
        content = build_disclosure_draft(events, confidential=confidential)
        now = datetime.now(UTC)
        if entity is None:
            entity = DisclosureDraft(project_id=project_id, content=content, created_at=now, updated_at=now)
            self.session.add(entity)
        else:
            entity.content = content
            entity.updated_at = now
        await self.session.flush()
        await self.session.refresh(entity)
        return DisclosureDraftRead.model_validate(entity)

    async def update_draft(self, draft_id: int, content: str) -> DisclosureDraftRead:
        entity = await self.session.get(DisclosureDraft, draft_id)
        if entity is None:
            raise NotFoundError("AI disclosure draft not found")
        entity.content = content
        entity.version += 1
        entity.updated_at = datetime.now(UTC)
        await self.session.flush()
        await self.session.refresh(entity)
        return DisclosureDraftRead.model_validate(entity)

    async def get_draft(self, draft_id: int) -> DisclosureDraftRead:
        entity = await self.session.get(DisclosureDraft, draft_id)
        if entity is None:
            raise NotFoundError("AI disclosure draft not found")
        return DisclosureDraftRead.model_validate(entity)

    async def _require_project(self, project_id: int) -> WritingProject:
        project = await self.session.get(WritingProject, project_id)
        if project is None:
            raise NotFoundError("Writing project not found")
        return project
