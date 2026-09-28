"""期刊指标批次与批量候选数据访问。"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.literature_search.model import (
    JournalMetricImportBatch,
    LiteratureCommercialJournalMetric,
)


class JournalMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_batches(
        self, offset: int, limit: int
    ) -> tuple[list[JournalMetricImportBatch], int]:
        total = int(
            (
                await self.session.scalar(
                    select(func.count()).select_from(JournalMetricImportBatch)
                )
            )
            or 0
        )
        result = await self.session.scalars(
            select(JournalMetricImportBatch)
            .order_by(
                JournalMetricImportBatch.created_at.desc(),
                JournalMetricImportBatch.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return list(result), total

    async def get_batch(self, batch_id: int) -> JournalMetricImportBatch | None:
        return await self.session.get(JournalMetricImportBatch, batch_id)

    async def get_batch_by_hash(
        self, file_hash: str
    ) -> JournalMetricImportBatch | None:
        return await self.session.scalar(
            select(JournalMetricImportBatch).where(
                JournalMetricImportBatch.source_file_hash == file_hash,
                JournalMetricImportBatch.status.in_(("ready", "active", "archived")),
            )
        )

    async def add_batch(
        self,
        batch: JournalMetricImportBatch,
        metrics: list[LiteratureCommercialJournalMetric],
    ) -> JournalMetricImportBatch:
        self.session.add(batch)
        await self.session.flush()
        for metric in metrics:
            metric.import_batch_id = batch.id
        self.session.add_all(metrics)
        await self.session.flush()
        return batch

    async def activate(self, batch: JournalMetricImportBatch) -> None:
        await self.session.execute(
            update(JournalMetricImportBatch)
            .where(
                JournalMetricImportBatch.provider == batch.provider,
                JournalMetricImportBatch.edition_year == batch.edition_year,
                JournalMetricImportBatch.id != batch.id,
                JournalMetricImportBatch.is_active.is_(True),
            )
            .values(is_active=False, status="ready", activated_at=None)
        )

    async def candidates(
        self, issns: set[str], names: set[str]
    ) -> list[LiteratureCommercialJournalMetric]:
        predicates: list[ColumnElement[bool]] = []
        if issns:
            predicates.extend(
                (
                    LiteratureCommercialJournalMetric.issn_l.in_(issns),
                    LiteratureCommercialJournalMetric.issn.in_(issns),
                    LiteratureCommercialJournalMetric.eissn.in_(issns),
                )
            )
        if names:
            predicates.append(
                LiteratureCommercialJournalMetric.normalized_journal_name.in_(names)
            )
        if not predicates:
            return []
        result = await self.session.scalars(
            select(LiteratureCommercialJournalMetric)
            .join(
                JournalMetricImportBatch,
                JournalMetricImportBatch.id
                == LiteratureCommercialJournalMetric.import_batch_id,
            )
            .where(JournalMetricImportBatch.is_active.is_(True), or_(*predicates))
        )
        return list(result)

    async def active_metrics_for_key(
        self, journal_key: str
    ) -> list[LiteratureCommercialJournalMetric]:
        result = await self.session.scalars(
            select(LiteratureCommercialJournalMetric)
            .join(
                JournalMetricImportBatch,
                JournalMetricImportBatch.id
                == LiteratureCommercialJournalMetric.import_batch_id,
            )
            .where(
                JournalMetricImportBatch.is_active.is_(True),
                LiteratureCommercialJournalMetric.journal_key == journal_key,
            )
            .order_by(LiteratureCommercialJournalMetric.metric_year.desc())
            .limit(10)
        )
        return list(result)

    async def has_active_batches(self) -> bool:
        return bool(
            await self.session.scalar(
                select(JournalMetricImportBatch.id)
                .where(JournalMetricImportBatch.is_active.is_(True))
                .limit(1)
            )
        )
