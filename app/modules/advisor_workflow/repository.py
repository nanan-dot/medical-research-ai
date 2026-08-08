"""Database access isolated from advisor workflow business rules."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advisor_workflow.model import AdvisorReview, DirectionRevision
from app.modules.research_direction.model import ResearchDirection


class AdvisorWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_direction(self, direction_id: int) -> ResearchDirection | None:
        return await self._session.get(ResearchDirection, direction_id)

    async def create_review(self, review: AdvisorReview) -> AdvisorReview:
        self._session.add(review)
        await self._session.flush()
        await self._session.refresh(review)
        return review

    async def list_reviews(self, direction_id: int) -> list[AdvisorReview]:
        result = await self._session.execute(
            select(AdvisorReview)
            .where(AdvisorReview.direction_id == direction_id)
            .order_by(AdvisorReview.id)
        )
        return list(result.scalars())

    async def create_revision(self, revision: DirectionRevision) -> DirectionRevision:
        self._session.add(revision)
        await self._session.flush()
        await self._session.refresh(revision)
        return revision

    async def list_revisions(self, direction_id: int) -> list[DirectionRevision]:
        result = await self._session.execute(
            select(DirectionRevision)
            .where(DirectionRevision.direction_id == direction_id)
            .order_by(DirectionRevision.version)
        )
        return list(result.scalars())

    async def save_direction(self, direction: ResearchDirection) -> ResearchDirection:
        await self._session.flush()
        await self._session.refresh(direction)
        return direction
