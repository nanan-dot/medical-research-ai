"""literature_search — 数据库访问"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.literature_search.model import (
    LiteratureSearch,
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

    async def list_records(self, offset: int = 0, limit: int = 20) -> list[LiteratureSearch]:
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

    async def create_result(self, entity: LiteratureSearchResult) -> LiteratureSearchResult:
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
            .order_by(LiteratureSearchTask.created_at.desc(), LiteratureSearchTask.id.desc())
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

    async def get_latest_version(self, task_id: int) -> LiteratureSearchResultVersion | None:
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
