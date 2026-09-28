"""Batched SQLAlchemy access for reading plans."""

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.literature_scoring.model import (
    LiteratureArticleScore,
    LiteratureResearchIntentSnapshot,
    LiteratureScoreGeneration,
)
from app.modules.literature_search.model import (
    LiteratureDuplicateGroupMember,
    LiteratureSearchItemState,
    LiteratureSearchResult,
)
from app.modules.reading_plan.model import ReadingPlan, ReadingPlanItem


class ReadingPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def result(self, result_id: int) -> LiteratureSearchResult | None:
        return await self.session.get(LiteratureSearchResult, result_id)

    async def next_version(self, result_id: int) -> int:
        value = await self.session.scalar(select(func.max(ReadingPlan.version)).where(ReadingPlan.result_id == result_id))
        return int(value or 0) + 1

    async def generation_context(self, result_id: int) -> tuple[dict[str, object] | None, set[str]]:
        generation = await self.session.scalar(
            select(LiteratureScoreGeneration)
            .where(LiteratureScoreGeneration.result_id == result_id, LiteratureScoreGeneration.status == "active")
            .order_by(LiteratureScoreGeneration.activated_at.desc(), LiteratureScoreGeneration.id.desc())
            .limit(1)
        )
        if generation is None:
            return None, set()
        snapshot = await self.session.get(LiteratureResearchIntentSnapshot, generation.intent_snapshot_id)
        if snapshot is None or snapshot.confirmation_status != "confirmed":
            return None, set()
        import json
        return json.loads(snapshot.dimensions_json), set()

    async def plans(self, result_id: int, limit: int, offset: int) -> tuple[int, list[ReadingPlan]]:
        total = await self.session.scalar(select(func.count()).select_from(ReadingPlan).where(ReadingPlan.result_id == result_id))
        rows = await self.session.scalars(
            select(ReadingPlan).options(selectinload(ReadingPlan.items)).where(ReadingPlan.result_id == result_id)
            .order_by(ReadingPlan.version.desc()).limit(limit).offset(offset)
        )
        return int(total or 0), list(rows)

    async def plan(self, plan_id: int) -> ReadingPlan | None:
        return await self.session.scalar(select(ReadingPlan).options(selectinload(ReadingPlan.items)).where(ReadingPlan.id == plan_id))

    async def active(self, result_id: int) -> ReadingPlan | None:
        return await self.session.scalar(select(ReadingPlan).options(selectinload(ReadingPlan.items)).where(ReadingPlan.result_id == result_id, ReadingPlan.status == "active"))

    async def add(self, plan: ReadingPlan) -> ReadingPlan:
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def archive_active(self, result_id: int) -> None:
        await self.session.execute(update(ReadingPlan).where(ReadingPlan.result_id == result_id, ReadingPlan.status == "active").values(status="archived"))

    async def states(self, result_id: int) -> dict[str, LiteratureSearchItemState]:
        rows = await self.session.scalars(select(LiteratureSearchItemState).where(LiteratureSearchItemState.result_id == result_id))
        return {row.pmid: row for row in rows}

    async def item(self, plan_id: int, pmid: str) -> ReadingPlanItem | None:
        return await self.session.scalar(select(ReadingPlanItem).where(ReadingPlanItem.plan_id == plan_id, ReadingPlanItem.pmid == pmid))

    async def active_scores(self, result_id: int) -> dict[str, LiteratureArticleScore]:
        """Bulk-load the published score generation for the snapshot."""
        generation_id = await self.session.scalar(
            select(LiteratureScoreGeneration.id)
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
        if generation_id is None:
            return {}
        rows = await self.session.scalars(
            select(LiteratureArticleScore).where(
                LiteratureArticleScore.generation_id == generation_id
            )
        )
        return {row.pmid: row for row in rows}

    async def hidden_duplicate_pmids(self, result_id: int) -> set[str]:
        """Return only records folded into another canonical record in this result."""
        rows = await self.session.scalars(
            select(LiteratureDuplicateGroupMember.record_pmid).where(
                LiteratureDuplicateGroupMember.result_id == result_id,
                LiteratureDuplicateGroupMember.canonical_result_id == result_id,
                LiteratureDuplicateGroupMember.canonical_record_pmid.is_not(None),
                LiteratureDuplicateGroupMember.canonical_record_pmid
                != LiteratureDuplicateGroupMember.record_pmid,
            )
        )
        return set(rows)
