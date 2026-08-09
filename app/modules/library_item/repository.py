"""library_item — 数据库访问（正式收藏记录）。"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.library_item.model import LibraryItem


class LibraryItemRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_by_identifier(
        self, pmid: str, doi: str | None
    ) -> LibraryItem | None:
        """按 PMID 或 DOI 精确查找（幂等去重用）。"""
        clauses = [LibraryItem.pmid == pmid]
        if doi:
            clauses.append(LibraryItem.doi == doi)
        result = await self.session.execute(select(LibraryItem).where(or_(*clauses)))
        return result.scalar_one_or_none()

    async def list_by_pmids(self, pmids: list[str]) -> list[LibraryItem]:
        """按 PMID 集合批量查询正式收藏。

        供阅读顺序等场景按 PMID 一次取回全文状态，避免对每条文献单独发查询。
        """
        if not pmids:
            return []
        result = await self.session.execute(
            select(LibraryItem).where(LibraryItem.pmid.in_(pmids))
        )
        return list(result.scalars().all())

    async def get(self, item_id: int) -> LibraryItem | None:
        result = await self.session.execute(
            select(LibraryItem).where(LibraryItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def list_items(
        self, offset: int, limit: int, status: str | None
    ) -> list[LibraryItem]:
        """分页列出收藏（按 id 倒序）；status 非空时按全文状态筛选。"""
        statement = select(LibraryItem).order_by(LibraryItem.id.desc())
        if status:
            statement = statement.where(LibraryItem.fulltext_status == status)
        result = await self.session.execute(statement.offset(offset).limit(limit))
        return list(result.scalars().all())

    async def count(self, status: str | None) -> int:
        statement = select(func.count()).select_from(LibraryItem)
        if status:
            statement = statement.where(LibraryItem.fulltext_status == status)
        return (await self.session.execute(statement)).scalar_one()

    async def create(self, item: LibraryItem) -> LibraryItem:
        """持久化新收藏并返回带 id 的实体。"""
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def save(self, item: LibraryItem) -> LibraryItem:
        """刷新已修改实体的持久化状态。"""
        await self.session.flush()
        await self.session.refresh(item)
        return item
