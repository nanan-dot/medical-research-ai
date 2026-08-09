"""Persistence operations for feasibility scoring."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.feasibility.model import FeasibilityScore, FeasibilityWeightProfile
from app.modules.research_direction.model import ResearchDirection


class FeasibilityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_direction(self, direction_id: int) -> ResearchDirection | None:
        return await self._session.get(ResearchDirection, direction_id)

    async def list_versions(self, direction_id: int) -> list[FeasibilityScore]:
        result = await self._session.execute(
            select(FeasibilityScore)
            .where(FeasibilityScore.direction_id == direction_id)
            .order_by(FeasibilityScore.version)
        )
        return list(result.scalars())

    async def list_latest_scores_for_matrix(
        self,
        evidence_matrix_id: int,
    ) -> list[FeasibilityScore]:
        """Return each active candidate's latest score in one evidence matrix."""
        result = await self._session.execute(
            select(FeasibilityScore)
            .join(ResearchDirection)
            .where(
                ResearchDirection.evidence_matrix_id == evidence_matrix_id,
                ResearchDirection.status == "active",
            )
            .order_by(FeasibilityScore.direction_id, FeasibilityScore.version.desc())
        )
        latest_by_direction: dict[int, FeasibilityScore] = {}
        for score in result.scalars():
            latest_by_direction.setdefault(score.direction_id, score)
        return list(latest_by_direction.values())

    async def get_default_profile(self) -> FeasibilityWeightProfile | None:
        result = await self._session.execute(
            select(FeasibilityWeightProfile).where(
                FeasibilityWeightProfile.is_default.is_(True)
            )
        )
        return result.scalar_one_or_none()

    async def create_score(self, entity: FeasibilityScore) -> FeasibilityScore:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity

    async def create_profile(
        self, entity: FeasibilityWeightProfile
    ) -> FeasibilityWeightProfile:
        self._session.add(entity)
        await self._session.flush()
        await self._session.refresh(entity)
        return entity
