"""可行性评分的数据访问。"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.feasibility.model import FeasibilityScore
from app.modules.research_direction.model import ResearchDirection
class FeasibilityRepository:
    def __init__(self, session: AsyncSession) -> None: self._session=session
    async def get_direction(self, direction_id:int)->ResearchDirection|None: return await self._session.get(ResearchDirection,direction_id)
    async def list_versions(self,direction_id:int)->list[FeasibilityScore]:
        result=await self._session.execute(select(FeasibilityScore).where(FeasibilityScore.direction_id==direction_id).order_by(FeasibilityScore.version)); return list(result.scalars())
    async def create(self,entity:FeasibilityScore)->FeasibilityScore: self._session.add(entity); await self._session.flush(); await self._session.refresh(entity); return entity
