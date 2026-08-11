"""literature_search — 数据库访问"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.literature_search.model import (
    LiteratureDuplicateGroup,
    LiteratureDuplicateResolution,
    LiteratureReadingOrder,
    LiteratureSearch,
    LiteratureSearchItemState,
    LiteratureSearchResult,
    LiteratureSearchResultVersion,
    LiteratureSearchTask,
)


class LiteratureSearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> LiteratureSearch | None:
        result = await self.session.execute(
            select(LiteratureSearch).where(LiteratureSearch.id == id)
        )
        return result.scalar_one_or_none()

    async def list_records(
        self, offset: int = 0, limit: int = 20
    ) -> list[LiteratureSearch]:
        result = await self.session.execute(
            select(LiteratureSearch).offset(offset).limit(limit)
        )
        return list(result.scalars().all())

    async def create(self, entity: LiteratureSearch) -> LiteratureSearch:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: LiteratureSearch) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    # ------------------------------------------------------------------
    # 检索结果持久化（WP03.5）
    # ------------------------------------------------------------------

    async def create_result(
        self, entity: LiteratureSearchResult
    ) -> LiteratureSearchResult:
        """保存一次检索结果并返回带 id 的实体。

        设计说明：flush 后 refresh 以拿到自增主键与 created_at，保证路由返回
        的 id 立即可用于后续 BibTeX 导出。
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_result(self, id: int) -> LiteratureSearchResult | None:
        result = await self.session.execute(
            select(LiteratureSearchResult).where(LiteratureSearchResult.id == id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # 检索任务（R2-WP04）
    # ------------------------------------------------------------------

    async def create_task(self, entity: LiteratureSearchTask) -> LiteratureSearchTask:
        """持久化一个 pending 任务并返回带 id 的实体。"""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def get_task(self, id: int) -> LiteratureSearchTask | None:
        """按 id 查询任务；结果版本通过 relationship 一并加载（懒加载由 session 管理）。"""
        result = await self.session.execute(
            select(LiteratureSearchTask).where(LiteratureSearchTask.id == id)
        )
        return result.scalar_one_or_none()

    async def get_task_by_fingerprint(
        self, fingerprint: str
    ) -> LiteratureSearchTask | None:
        result = await self.session.execute(
            select(LiteratureSearchTask).where(
                LiteratureSearchTask.strategy_fingerprint == fingerprint
            )
        )
        return result.scalar_one_or_none()

    async def list_tasks_for_fingerprint_matching(self) -> list[LiteratureSearchTask]:
        """读取旧任务以便首次按新规则认领其策略，不修改历史快照。"""
        result = await self.session.execute(select(LiteratureSearchTask))
        return list(result.scalars().all())

    async def list_tasks(
        self, offset: int = 0, limit: int = 20
    ) -> tuple[list[LiteratureSearchTask], int]:
        """分页查询任务历史（按创建时间倒序），返回 (条目, 总数)。

        设计说明：列表页只读任务自身字段（不含 items_json），结果明细通过
        GET /{id} 按需加载，避免一次返回大量历史数据。
        """
        count_result = await self.session.execute(
            select(func.count(LiteratureSearchTask.id))
        )
        total = int(count_result.scalar_one())
        result = await self.session.execute(
            select(LiteratureSearchTask)
            .order_by(
                LiteratureSearchTask.created_at.desc(), LiteratureSearchTask.id.desc()
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_task_versions(
        self, task_id: int
    ) -> list[LiteratureSearchResultVersion]:
        """返回任务的全部结果版本（按版本号升序）。

        设计说明：版本号从 1 递增，升序即重跑顺序；用于详情页展示版本时间线。
        """
        result = await self.session.execute(
            select(LiteratureSearchResultVersion)
            .where(LiteratureSearchResultVersion.task_id == task_id)
            .order_by(LiteratureSearchResultVersion.version.asc())
        )
        return list(result.scalars().all())

    async def get_latest_version(
        self, task_id: int
    ) -> LiteratureSearchResultVersion | None:
        """返回任务最近一个结果版本（用于重跑时对比变化）。"""
        result = await self.session.execute(
            select(LiteratureSearchResultVersion)
            .where(LiteratureSearchResultVersion.task_id == task_id)
            .order_by(LiteratureSearchResultVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create_result_version(
        self, task_id: int, result_id: int, version: int
    ) -> LiteratureSearchResultVersion:
        """把一次执行结果挂到任务上，version 由调用方按"当前最大版本 +1"计算。"""
        entity = LiteratureSearchResultVersion(
            task_id=task_id, result_id=result_id, version=version
        )
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def save_task(self, entity: LiteratureSearchTask) -> LiteratureSearchTask:
        """提交对任务字段（status/result_count/searched_at/latest_result_id 等）的更新。"""
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    # ------------------------------------------------------------------
    # 检索结果用户态（R2-WP05，manage-refs 融合）
    # ------------------------------------------------------------------

    async def get_item_states(
        self, result_id: int
    ) -> dict[str, LiteratureSearchItemState]:
        """返回某结果快照下全部用户态记录（按 PMID 索引）。

        设计说明：结果页每次展示最多 page_size（≤100）条，这里一次性读取
        该结果下全部用户态记录（规模 = 已产生用户操作的条目数），在内存中
        按 PMID 查找，避免对每条结果单独发查询。
        """
        result = await self.session.execute(
            select(LiteratureSearchItemState).where(
                LiteratureSearchItemState.result_id == result_id
            )
        )
        return {state.pmid: state for state in result.scalars().all()}

    async def get_item_state(
        self, result_id: int, pmid: str
    ) -> LiteratureSearchItemState | None:
        """按结果 id + PMID 查询单条用户态记录。"""
        result = await self.session.execute(
            select(LiteratureSearchItemState).where(
                LiteratureSearchItemState.result_id == result_id,
                LiteratureSearchItemState.pmid == pmid,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_item_state(
        self, entity: LiteratureSearchItemState
    ) -> LiteratureSearchItemState:
        """写入或更新单条用户态记录。

        设计说明：复合主键（result_id, pmid）已约束唯一性；先查后写避免
        SQLite 的 INSERT OR REPLACE 触发外键级联删除（SQLite 的 replace
        会先删旧行再插新行，可能错误触发 ondelete CASCADE）。调用方必须
        传入已合并好的完整实体（四个字段均为最终值），本方法不感知
        "哪些字段被更新"。
        """
        existing = await self.get_item_state(entity.result_id, entity.pmid)
        if existing is not None:
            existing.saved = entity.saved
            existing.read_status = entity.read_status
            existing.tags_json = entity.tags_json
            existing.custom_order_index = entity.custom_order_index
            entity = existing
        else:
            self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    # ------------------------------------------------------------------
    # 可撤销去重决策（R2-WP06）
    # ------------------------------------------------------------------

    async def latest_task_results(self) -> list[tuple[int, LiteratureSearchResult]]:
        """返回每个任务的当前结果快照，以便跨任务识别重复且不扫描历史版本。"""
        result = await self.session.execute(
            select(LiteratureSearchTask.id, LiteratureSearchResult)
            .join(
                LiteratureSearchResult,
                LiteratureSearchTask.latest_result_id == LiteratureSearchResult.id,
            )
            .where(LiteratureSearchTask.latest_result_id.is_not(None))
        )
        return [(row[0], row[1]) for row in result.all()]

    async def delete_groups_for_task(self, task_id: int) -> None:
        """重跑去重时仅替换该任务触发的旧决策，不影响其他任务的审计记录。"""
        await self.session.execute(
            delete(LiteratureDuplicateGroup).where(
                LiteratureDuplicateGroup.trigger_task_id == task_id
            )
        )
        await self.session.flush()

    async def create_duplicate_group(
        self, entity: LiteratureDuplicateGroup
    ) -> LiteratureDuplicateGroup:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def list_duplicate_groups(self) -> list[LiteratureDuplicateGroup]:
        result = await self.session.execute(
            select(LiteratureDuplicateGroup)
            .options(
                selectinload(LiteratureDuplicateGroup.members),
                selectinload(LiteratureDuplicateGroup.resolution),
            )
            .order_by(
                LiteratureDuplicateGroup.created_at.desc(),
                LiteratureDuplicateGroup.id.desc(),
            )
        )
        return list(result.scalars().all())

    async def get_duplicate_group(
        self, group_id: int
    ) -> LiteratureDuplicateGroup | None:
        result = await self.session.execute(
            select(LiteratureDuplicateGroup)
            .where(LiteratureDuplicateGroup.id == group_id)
            .options(
                selectinload(LiteratureDuplicateGroup.members),
                selectinload(LiteratureDuplicateGroup.resolution),
            )
        )
        return result.scalar_one_or_none()

    async def save_duplicate_group(
        self, entity: LiteratureDuplicateGroup
    ) -> LiteratureDuplicateGroup:
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def replace_duplicate_resolution(
        self, entity: LiteratureDuplicateResolution
    ) -> LiteratureDuplicateResolution:
        existing = await self.session.execute(
            select(LiteratureDuplicateResolution).where(
                LiteratureDuplicateResolution.group_id == entity.group_id
            )
        )
        prior = existing.scalar_one_or_none()
        if prior is not None:
            await self.session.delete(prior)
            await self.session.flush()
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete_duplicate_resolution(
        self, entity: LiteratureDuplicateResolution
    ) -> None:
        await self.session.delete(entity)
        await self.session.flush()

    # ------------------------------------------------------------------
    # 阅读顺序人工顺序持久化（R2-WP08，manage-refs 融合）
    # ------------------------------------------------------------------

    async def get_reading_order(self, result_id: int) -> LiteratureReadingOrder | None:
        """读取某结果快照下的人工顺序记录（无则返回 None）。"""
        result = await self.session.execute(
            select(LiteratureReadingOrder).where(
                LiteratureReadingOrder.result_id == result_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert_reading_order(
        self, entity: LiteratureReadingOrder
    ) -> LiteratureReadingOrder:
        """写入或更新人工顺序。

        设计说明：result_id 唯一约束已保证每个结果只有一份人工顺序；先查
        后写避免 SQLite 的 INSERT OR REPLACE 触发外键级联删除（与
        upsert_item_state 的处理一致）。调用方须传入完整实体。
        """
        existing = await self.get_reading_order(entity.result_id)
        if existing is not None:
            existing.manual_order_json = entity.manual_order_json
            existing.updated_at = entity.updated_at
            entity = existing
        else:
            self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity
