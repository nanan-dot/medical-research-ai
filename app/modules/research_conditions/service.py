"""研究条件快照业务逻辑。"""

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.research_conditions.model import ResearchConditions, ResearchConditionsVersion
from app.modules.research_conditions.repository import ResearchConditionsRepository
from app.modules.research_conditions.schema import (
    ResearchConditionsCreate,
    ResearchConditionsInput,
    ResearchConditionsPatch,
    ResearchConditionsRead,
)


class ResearchConditionsService:
    """保存和读取条件版本；本工作包不调用模型，也不推断未知字段。"""

    def __init__(self, session: AsyncSession):
        self._repository = ResearchConditionsRepository(session)

    async def create(self, payload: ResearchConditionsCreate) -> ResearchConditionsRead:
        entity = await self._repository.create(ResearchConditions(current_version=1))
        version = await self._repository.create_version(
            self._new_version(entity.id, 1, payload)
        )
        return self._to_read(entity, version)

    async def get(self, conditions_id: int) -> ResearchConditionsRead:
        entity = await self._get_entity(conditions_id)
        version = await self._get_version(entity.id, entity.current_version)
        return self._to_read(entity, version)

    async def patch(
        self, conditions_id: int, payload: ResearchConditionsPatch
    ) -> ResearchConditionsRead:
        entity = await self._get_entity(conditions_id)
        current_version = await self._get_version(entity.id, entity.current_version)
        merged_payload = self._merge_patch(current_version, payload)
        next_version = entity.current_version + 1
        version = await self._repository.create_version(
            self._new_version(entity.id, next_version, merged_payload)
        )
        entity.current_version = next_version
        entity.updated_at = datetime.now(UTC)
        entity = await self._repository.save(entity)
        return self._to_read(entity, version)

    async def _get_entity(self, conditions_id: int) -> ResearchConditions:
        entity = await self._repository.get(conditions_id)
        if entity is None:
            raise NotFoundError(f"Research conditions not found: {conditions_id}")
        return entity

    async def _get_version(self, conditions_id: int, version: int) -> ResearchConditionsVersion:
        entity = await self._repository.get_version(conditions_id, version)
        if entity is None:
            raise NotFoundError(f"Research conditions version not found: {conditions_id}/{version}")
        return entity

    @staticmethod
    def _new_version(
        conditions_id: int, version: int, payload: ResearchConditionsInput
    ) -> ResearchConditionsVersion:
        snapshot = payload.model_dump(exclude={"uncertain_notes"}, mode="json", exclude_none=True)
        return ResearchConditionsVersion(
            conditions_id=conditions_id,
            version=version,
            conditions_json=json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")),
            uncertain_notes=payload.uncertain_notes,
        )

    @staticmethod
    def _to_read(
        entity: ResearchConditions, version: ResearchConditionsVersion
    ) -> ResearchConditionsRead:
        snapshot = json.loads(version.conditions_json)
        return ResearchConditionsRead(
            id=entity.id,
            conditions_version=version.version,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            uncertain_notes=version.uncertain_notes,
            **snapshot,
        )

    @staticmethod
    def _merge_patch(
        current_version: ResearchConditionsVersion, patch: ResearchConditionsPatch
    ) -> ResearchConditionsCreate:
        """把局部修改合成为完整快照，确保 PATCH 不会意外清空未提交字段。"""
        snapshot = json.loads(current_version.conditions_json)
        patch_data = patch.model_dump(exclude_unset=True, mode="json")
        if "uncertain_notes" not in patch_data:
            patch_data["uncertain_notes"] = current_version.uncertain_notes
        snapshot.update(patch_data)
        return ResearchConditionsCreate.model_validate(snapshot)
