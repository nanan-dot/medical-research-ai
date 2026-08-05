"""literature_search — 数据库访问"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.literature_search.model import LiteratureSearch, LiteratureSearchResult


class LiteratureSearchRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, id: int) -> LiteratureSearch | None:
        result = await self.session.execute(
            select(LiteratureSearch).where(LiteratureSearch.id == id)
        )
        return result.scalar_one_or_none()

    async def list(self, offset: int = 0, limit: int = 20) -> list[LiteratureSearch]:
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
    # 检索结果持久化
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
