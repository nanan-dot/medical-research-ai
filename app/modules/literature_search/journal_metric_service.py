"""期刊指标导入批次生命周期与查询编排。"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.common.exceptions import NotFoundError
from app.core.config import settings
from app.modules.literature_search.journal_metric_import import (
    JournalMetricImportError,
    parse_journal_metric_csv,
)
from app.modules.literature_search.journal_metric_normalization import (
    normalize_journal_name,
)
from app.modules.literature_search.journal_metric_repository import (
    JournalMetricRepository,
)
from app.modules.literature_search.journal_metric_schema import (
    JournalMetricImportBatchList,
    JournalMetricImportBatchRead,
    JournalMetricImportPreview,
)
from app.modules.literature_search.model import (
    JournalMetricImportBatch,
    LiteratureCommercialJournalMetric,
)

ACTIVE_YEAR_LIMIT = 10


class JournalMetricService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = JournalMetricRepository(session)

    async def preview(self, file: UploadFile) -> JournalMetricImportPreview:
        parsed = await parse_journal_metric_csv(
            file, settings.JOURNAL_METRIC_IMPORT_MAX_BYTES
        )
        if not parsed.preview.is_committable:
            raise _error(
                "journal_metric_invalid_rows",
                "CSV contains invalid rows",
                parsed.preview.model_dump(),
            )
        return parsed.preview

    async def commit(
        self,
        file: UploadFile,
        *,
        expected_file_hash: str,
        provider: str,
        provider_version: str,
        edition_year: int,
        license_provenance: str,
    ) -> JournalMetricImportBatchRead:
        parsed = await parse_journal_metric_csv(
            file, settings.JOURNAL_METRIC_IMPORT_MAX_BYTES
        )
        if parsed.file_hash != expected_file_hash:
            raise _error(
                "journal_metric_preview_mismatch", "uploaded CSV differs from preview"
            )
        if not parsed.preview.is_committable:
            raise _error(
                "journal_metric_invalid_rows",
                "CSV contains invalid rows",
                parsed.preview.model_dump(),
            )
        if any(row.metric_year != edition_year for row in parsed.rows):
            raise _error(
                "journal_metric_year_out_of_range",
                "every metric_year must equal edition_year",
            )
        if await self.repository.get_batch_by_hash(parsed.file_hash):
            raise _error(
                "journal_metric_duplicate_import", "this file was already imported"
            )
        batch = JournalMetricImportBatch(
            edition_year=edition_year,
            provider=provider,
            provider_version=provider_version,
            source_filename=parsed.filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1],
            source_file_hash=parsed.file_hash,
            license_provenance=license_provenance,
            record_count=len(parsed.rows),
            status="ready",
            is_active=False,
        )
        metrics = [
            self._to_model(row, provider, provider_version, license_provenance)
            for row in parsed.rows
        ]
        try:
            await self.repository.add_batch(batch, metrics)
        except IntegrityError as error:
            await self.session.rollback()
            raise _error(
                "journal_metric_duplicate_import",
                "provider year/version or journal key already exists",
            ) from error
        return JournalMetricImportBatchRead.model_validate(batch)

    async def list_batches(
        self, offset: int, limit: int
    ) -> JournalMetricImportBatchList:
        batches, total = await self.repository.list_batches(offset, limit)
        return JournalMetricImportBatchList(
            total=total,
            offset=offset,
            limit=limit,
            items=[
                JournalMetricImportBatchRead.model_validate(batch) for batch in batches
            ],
        )

    async def activate(self, batch_id: int) -> JournalMetricImportBatchRead:
        batch = await self._batch(batch_id)
        if batch.status not in {"ready", "active"}:
            raise _error(
                "journal_metric_batch_not_ready",
                "batch must be ready before activation",
            )
        await self.repository.activate(batch)
        batch.status = "active"
        batch.is_active = True
        batch.activated_at = datetime.now(UTC)
        await self._archive_old_active_years()
        await self.session.flush()
        return JournalMetricImportBatchRead.model_validate(batch)

    async def archive(self, batch_id: int) -> JournalMetricImportBatchRead:
        batch = await self._batch(batch_id)
        batch.status = "archived"
        batch.is_active = False
        batch.activated_at = None
        await self.session.flush()
        return JournalMetricImportBatchRead.model_validate(batch)

    async def _batch(self, batch_id: int) -> JournalMetricImportBatch:
        batch = await self.repository.get_batch(batch_id)
        if batch is None:
            error = NotFoundError(f"JournalMetricImportBatch not found: {batch_id}")
            error.code = "journal_metric_batch_not_found"
            raise error
        return batch

    async def _archive_old_active_years(self) -> None:
        years = list(
            await self.session.scalars(
                select(JournalMetricImportBatch.edition_year)
                .where(JournalMetricImportBatch.is_active.is_(True))
                .distinct()
                .order_by(JournalMetricImportBatch.edition_year.desc())
            )
        )
        if len(years) <= ACTIVE_YEAR_LIMIT:
            return
        await self.session.execute(
            update(JournalMetricImportBatch)
            .where(
                JournalMetricImportBatch.is_active.is_(True),
                JournalMetricImportBatch.edition_year.in_(years[ACTIVE_YEAR_LIMIT:]),
            )
            .values(is_active=False, status="archived", activated_at=None)
        )

    @staticmethod
    def _to_model(
        row: object, provider: str, provider_version: str, license_provenance: str
    ) -> LiteratureCommercialJournalMetric:
        from app.modules.literature_search.journal_metric_schema import JournalMetricRow

        assert isinstance(row, JournalMetricRow)
        normalized_name = normalize_journal_name(row.journal_name)
        journal_key = row.issn_l or row.issn or row.eissn or normalized_name
        assert journal_key is not None
        return LiteratureCommercialJournalMetric(
            journal_key=journal_key,
            journal_name=row.journal_name,
            normalized_journal_name=normalized_name,
            issn=row.issn,
            eissn=row.eissn,
            issn_l=row.issn_l,
            metric_year=row.metric_year,
            impact_factor=row.impact_factor,
            impact_factor_year=row.impact_factor_year,
            jcr_best_quartile=row.jcr_best_quartile,
            jcr_year=row.jcr_year,
            wos_indexes_json=json.dumps(row.wos_indexes),
            wos_year=row.wos_year,
            cas_quartile=row.cas_quartile,
            cas_year=row.cas_year,
            cas_category=row.cas_category,
            is_cas_top=row.is_cas_top,
            warning_status=row.warning_status,
            provider=provider,
            provider_version=provider_version,
            license_provenance=license_provenance,
            status="available",
            observed_at=datetime.now(UTC),
        )


def _error(code: str, message: str, detail: object = None) -> JournalMetricImportError:
    error = JournalMetricImportError(message, detail=detail)
    error.code = code
    return error
