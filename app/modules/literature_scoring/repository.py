"""Small persistence boundary for atomic generation selection."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.literature_scoring.model import (
    LiteratureArticleScore,
    LiteratureResearchIntentSnapshot,
    LiteratureScoreGeneration,
)


class LiteratureScoringRepository:
    """Generation queries never expose a building generation as active."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_generation_by_fingerprint(
        self, result_id: int, fingerprint: str
    ) -> LiteratureScoreGeneration | None:
        result = await self.session.execute(
            select(LiteratureScoreGeneration).where(
                LiteratureScoreGeneration.result_id == result_id,
                LiteratureScoreGeneration.input_fingerprint == fingerprint,
            )
        )
        return result.scalar_one_or_none()

    async def get_active_generation(
        self, result_id: int
    ) -> LiteratureScoreGeneration | None:
        result = await self.session.execute(
            select(LiteratureScoreGeneration)
            .where(
                LiteratureScoreGeneration.result_id == result_id,
                LiteratureScoreGeneration.status == "active",
            )
            .order_by(
                LiteratureScoreGeneration.activated_at.desc(),
                LiteratureScoreGeneration.id.desc(),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_building_generation(
        self, result_id: int
    ) -> LiteratureScoreGeneration | None:
        result = await self.session.execute(
            select(LiteratureScoreGeneration)
            .where(
                LiteratureScoreGeneration.result_id == result_id,
                LiteratureScoreGeneration.status.in_(
                    ("queued", "collecting_inputs", "scoring", "validating")
                ),
            )
            .order_by(LiteratureScoreGeneration.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_generation(
        self, generation_id: int
    ) -> LiteratureScoreGeneration | None:
        result = await self.session.execute(
            select(LiteratureScoreGeneration).where(
                LiteratureScoreGeneration.id == generation_id
            )
        )
        return result.scalar_one_or_none()

    async def get_latest_generation(
        self, result_id: int
    ) -> LiteratureScoreGeneration | None:
        result = await self.session.execute(
            select(LiteratureScoreGeneration)
            .where(LiteratureScoreGeneration.result_id == result_id)
            .order_by(LiteratureScoreGeneration.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self, generation: LiteratureScoreGeneration
    ) -> LiteratureScoreGeneration:
        self.session.add(generation)
        await self.session.flush()
        await self.session.refresh(generation)
        return generation

    async def get_confirmed_intent(
        self, intent_id: int
    ) -> LiteratureResearchIntentSnapshot | None:
        result = await self.session.execute(
            select(LiteratureResearchIntentSnapshot).where(
                LiteratureResearchIntentSnapshot.id == intent_id,
                LiteratureResearchIntentSnapshot.confirmation_status
                == "user_confirmed",
            )
        )
        return result.scalar_one_or_none()

    async def get_intent_by_fingerprint(
        self, research_context_id: int, fingerprint: str
    ) -> LiteratureResearchIntentSnapshot | None:
        result = await self.session.execute(
            select(LiteratureResearchIntentSnapshot).where(
                LiteratureResearchIntentSnapshot.research_context_id
                == research_context_id,
                LiteratureResearchIntentSnapshot.fingerprint == fingerprint,
            )
        )
        return result.scalar_one_or_none()

    async def create_intent(
        self, intent: LiteratureResearchIntentSnapshot
    ) -> LiteratureResearchIntentSnapshot:
        self.session.add(intent)
        await self.session.flush()
        await self.session.refresh(intent)
        return intent

    async def add_scores(self, scores: list[LiteratureArticleScore]) -> None:
        self.session.add_all(scores)
        await self.session.flush()

    async def get_active_scores(
        self, result_id: int
    ) -> dict[str, LiteratureArticleScore]:
        active = await self.get_active_generation(result_id)
        if active is None:
            return {}
        result = await self.session.execute(
            select(LiteratureArticleScore).where(
                LiteratureArticleScore.generation_id == active.id
            )
        )
        return {score.pmid: score for score in result.scalars().all()}

    async def get_active_score(
        self, result_id: int, pmid: str
    ) -> tuple[LiteratureScoreGeneration, LiteratureArticleScore] | None:
        generation = await self.get_active_generation(result_id)
        if generation is None:
            return None
        result = await self.session.execute(
            select(LiteratureArticleScore).where(
                LiteratureArticleScore.generation_id == generation.id,
                LiteratureArticleScore.pmid == pmid,
            )
        )
        score = result.scalar_one_or_none()
        return (generation, score) if score is not None else None
