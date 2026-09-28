"""Short-transaction orchestration for anchored translation jobs and revisions."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_layout.model import DocumentLayoutSegment
from app.modules.document_selection.model import DocumentAnchorSegment
from app.modules.document_selection.schema import (
    SelectionFragment,
    SourceAnchorDescriptor,
)
from app.modules.document_selection.service import SourceAnchorService
from app.modules.medical_translation.constants import (
    CONFIG_VERSION,
    POLICY_VERSION,
    PROMPT_VERSION,
    TASK_TYPE,
    TERMINOLOGY_VERSION,
    VALIDATOR_VERSION,
)
from app.modules.medical_translation.errors import (
    TranslationConflictError,
    TranslationStateError,
)
from app.modules.medical_translation.model import (
    MedicalTranslationJob,
    TranslationReview,
    TranslationRevision,
    TranslationTermOverride,
    TranslationValidationReport,
)
from app.modules.medical_translation.quality import QualityIssue, validate_translation
from app.modules.medical_translation.schema import (
    TranslationCorrectionCreate,
    TranslationJobCreate,
    TranslationJobRead,
    TranslationPrefetchIntentRead,
    TranslationRevisionRead,
    TranslationSegmentIntentCreate,
    TranslationSegmentStatusRead,
    TranslationTermOverrideCreate,
    TranslationTermOverrideRead,
)
from app.modules.task.model import TaskRecord


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class MedicalTranslationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_job(
        self, document_id: int, payload: TranslationJobCreate, idempotency_key: str
    ) -> TranslationJobRead:
        request_fingerprint = _digest(
            json.dumps(
                payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
            )
        )
        existing = await self._session.scalar(
            select(MedicalTranslationJob).where(
                MedicalTranslationJob.document_id == document_id,
                MedicalTranslationJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if existing.request_fingerprint != request_fingerprint:
                raise TranslationConflictError(
                    "Idempotency key was reused with a different request"
                )
            await self._authorize_job(existing)
            return self._job_read(existing)

        if payload.anchor_descriptor is not None:
            anchor_read = await SourceAnchorService(self._session).create(
                document_id, payload.anchor_descriptor
            )
        else:
            assert payload.source_anchor_id is not None
            anchor_read = await SourceAnchorService(self._session).get(
                payload.source_anchor_id, document_id, require_current=True
            )
        anchor = await self._session.get(DocumentSourceAnchor, anchor_read.id)
        if anchor is None:
            raise NotFoundError("Source anchor not found")
        if len(anchor.quote) > 8000:
            raise TranslationConflictError(
                "Selection exceeds the Phase 1 character limit"
            )
        membership = await self._session.scalar(
            select(DocumentAnchorSegment)
            .where(DocumentAnchorSegment.anchor_id == anchor.id)
            .order_by(DocumentAnchorSegment.segmentation_revision_id.desc())
        )
        if membership is None:
            raise TranslationConflictError("Selection has no current layout membership")
        task_key = f"translation:{document_id}:{idempotency_key}"
        task = TaskRecord(
            task_type=TASK_TYPE,
            title="医学选区翻译",
            status="queued",
            progress=0,
            phase="queued",
            completed_units=0,
            total_units=1,
            source_type="document",
            source_id=document_id,
            detail_json=json.dumps({"document_id": document_id}, separators=(",", ":")),
            idempotency_key=task_key,
            active_idempotency_key=task_key,
        )
        self._session.add(task)
        await self._session.flush()
        job = MedicalTranslationJob(
            task_id=task.id,
            document_id=document_id,
            source_anchor_id=anchor.id,
            anchor_revision_id=anchor.anchor_revision_id,
            segmentation_revision_id=membership.segmentation_revision_id,
            source_text_hash=anchor.quote_hash,
            source_language=payload.source_language,
            target_language=payload.target_language,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            state="queued",
            request_priority=3,
            request_trigger="selection",
        )
        self._session.add(job)
        await self._session.flush()
        task.detail_json = json.dumps(
            {"document_id": document_id, "translation_job_id": job.id},
            separators=(",", ":"),
        )
        return self._job_read(job)

    async def get_job(self, job_id: int) -> TranslationJobRead:
        job = await self._job(job_id)
        await self._authorize_job(job)
        return self._job_read(job)

    async def request_segments(
        self,
        document_id: int,
        payload: TranslationSegmentIntentCreate,
    ) -> TranslationPrefetchIntentRead:
        """Queue eligible A1 segments through the same immutable A2 anchor pipeline."""
        document = await AnchorQueries(self._session).authorized_document(document_id)
        if document.file_hash != payload.expected_file_hash:
            raise TranslationConflictError("Document file revision changed")
        anchor_revision = await self._session.get(
            DocumentAnchorRevision, payload.expected_anchor_revision_id
        )
        if anchor_revision is None or anchor_revision.document_id != document_id:
            raise TranslationConflictError("Anchor revision does not belong to document")
        segments = list(
            (
                await self._session.scalars(
                    select(DocumentLayoutSegment)
                    .where(
                        DocumentLayoutSegment.id.in_(payload.segment_ids),
                        DocumentLayoutSegment.segmentation_revision_id
                        == payload.expected_segmentation_revision_id,
                    )
                    .order_by(DocumentLayoutSegment.reading_order)
                )
            ).all()
        )
        if len(segments) != len(set(payload.segment_ids)):
            raise TranslationConflictError("Segments are stale or do not belong to this revision")
        items: list[TranslationSegmentStatusRead] = []
        queued_count = 0
        deduplicated_count = 0
        for segment in segments:
            if segment.translation_eligibility != "eligible":
                items.append(
                    TranslationSegmentStatusRead(
                        segment_id=segment.id,
                        translation_eligibility=segment.translation_eligibility,
                        state="degraded",
                        degraded_reason="layout_review_required"
                        if segment.translation_eligibility == "review_required"
                        else "layout_not_translatable",
                    )
                )
                continue
            job = await self._latest_segment_job(document_id, segment.id)
            if job is not None and job.state in {"queued", "running", "quality_checking", "succeeded"}:
                revision = (
                    await self._session.get(TranslationRevision, job.result_revision_id)
                    if job.result_revision_id is not None
                    else None
                )
                if (
                    revision is not None
                    and revision.origin == "machine"
                    and (
                        revision.provider
                        in {
                            "local-transformers-mbart-paramed",
                            "local-transformers-marian",
                        }
                        or revision.prompt_version != PROMPT_VERSION
                        or revision.config_version != CONFIG_VERSION
                        or revision.policy_version != POLICY_VERSION
                        or revision.validator_version != VALIDATOR_VERSION
                    )
                ):
                    job = None
                else:
                    items.append(
                        TranslationSegmentStatusRead(
                            segment_id=segment.id,
                            translation_eligibility=segment.translation_eligibility,
                            state=(
                                "cached"
                                if revision is not None
                                else "queued"
                                if job.state == "queued"
                                else "running"
                            ),
                            job=self._job_read(job),
                            revision=await self.revision_read(revision) if revision else None,
                        )
                    )
                    deduplicated_count += 1
                    continue
            try:
                descriptor = await self._segment_descriptor(
                    document_id, document.file_hash, anchor_revision.id,
                    payload.expected_segmentation_revision_id, segment,
                )
            except ValidationError:
                items.append(
                    TranslationSegmentStatusRead(
                        segment_id=segment.id,
                        translation_eligibility=segment.translation_eligibility,
                        state="degraded",
                        degraded_reason="segment_exceeds_translation_limits",
                    )
                )
                continue
            idempotency_key = self._segment_idempotency_key(payload, segment.id)
            created = await self.create_job(
                document_id,
                TranslationJobCreate(
                    anchor_descriptor=descriptor,
                    source_language=payload.source_language,
                    target_language=payload.target_language,
                ),
                idempotency_key,
            )
            row = await self._job(created.id)
            row.layout_segment_id = segment.id
            row.request_priority = 3 if segment.id == payload.active_segment_id else 2 if payload.trigger == "visible" else 1
            row.request_trigger = payload.trigger
            items.append(
                TranslationSegmentStatusRead(
                    segment_id=segment.id,
                    translation_eligibility=segment.translation_eligibility,
                    state="queued",
                    job=self._job_read(row),
                )
            )
            queued_count += 1
        await self._session.flush()
        return TranslationPrefetchIntentRead(
            generation=f"{document_id}:{anchor_revision.id}:{payload.expected_segmentation_revision_id}",
            items=items,
            queued_count=queued_count,
            deduplicated_count=deduplicated_count,
        )

    async def _segment_descriptor(
        self,
        document_id: int,
        file_hash: str,
        anchor_revision_id: int,
        segmentation_revision_id: int,
        segment: DocumentLayoutSegment,
    ) -> SourceAnchorDescriptor:
        from app.modules.document_anchor.model import (
            DocumentSourcePage,
            DocumentSourceTextItem,
        )
        from app.modules.document_layout.model import (
            DocumentLayoutBlock,
            DocumentLayoutFragment,
        )

        fragments = list(
            (
                await self._session.scalars(
                    select(DocumentLayoutFragment)
                    .where(DocumentLayoutFragment.segment_id == segment.id)
                    .order_by(DocumentLayoutFragment.fragment_order)
                )
            ).all()
        )
        selection_fragments: list[SelectionFragment] = []
        for fragment in fragments:
            page = await self._session.get(DocumentSourcePage, fragment.page_id)
            if page is None:
                raise TranslationConflictError("Segment source page is missing")
            blocks = list(
                (
                    await self._session.scalars(
                        select(DocumentLayoutBlock).where(
                            DocumentLayoutBlock.segmentation_revision_id
                            == segmentation_revision_id,
                            DocumentLayoutBlock.page_id == fragment.page_id,
                        )
                    )
                ).all()
            )
            candidates = [
                json.loads(block.item_indexes_json)
                for block in blocks
                if block.block_type not in {"header", "footer"}
                and json.loads(block.item_indexes_json)
                and min(json.loads(block.item_indexes_json))
                == fragment.start_item_index
                and max(json.loads(block.item_indexes_json))
                == fragment.end_item_index
            ]
            if len(candidates) != 1:
                raise TranslationConflictError("Segment reading order is ambiguous")
            source_items = list(
                (
                    await self._session.scalars(
                        select(DocumentSourceTextItem)
                        .where(
                            DocumentSourceTextItem.page_id == page.id,
                            DocumentSourceTextItem.item_index.in_(candidates[0]),
                        )
                    )
                ).all()
            )
            by_index = {item.item_index: item for item in source_items}
            if any(item_index not in by_index for item_index in candidates[0]):
                raise TranslationConflictError("Segment text mapping is incomplete")
            for item_index in candidates[0]:
                item = by_index[item_index]
                if not item.raw_text:
                    continue
                selection_fragments.append(
                    SelectionFragment(
                        page_number=page.page_number,
                        start_item_index=item_index,
                        start_offset_utf16=0,
                        end_item_index=item_index,
                        end_offset_utf16=item.raw_utf16_length,
                    )
                )
        if not selection_fragments:
            raise TranslationConflictError("Segment has no stable source fragments")
        return SourceAnchorDescriptor(
            expected_file_hash=file_hash,
            expected_anchor_revision_id=anchor_revision_id,
            expected_segmentation_revision_id=segmentation_revision_id,
            browser_quote=segment.text,
            fragments=selection_fragments,
        )

    async def _latest_segment_job(
        self, document_id: int, segment_id: int
    ) -> MedicalTranslationJob | None:
        return await self._session.scalar(
            select(MedicalTranslationJob)
            .where(
                MedicalTranslationJob.document_id == document_id,
                MedicalTranslationJob.layout_segment_id == segment_id,
            )
            .order_by(MedicalTranslationJob.created_at.desc(), MedicalTranslationJob.id.desc())
        )

    @staticmethod
    def _segment_idempotency_key(
        payload: TranslationSegmentIntentCreate, segment_id: int
    ) -> str:
        return "phase2-" + _digest(
            f"{payload.expected_file_hash}:{payload.expected_anchor_revision_id}:"
            f"{payload.expected_segmentation_revision_id}:{segment_id}:"
            f"{payload.source_language}:{payload.target_language}:"
            f"{PROMPT_VERSION}:{CONFIG_VERSION}:{POLICY_VERSION}:"
            f"{TERMINOLOGY_VERSION}:{VALIDATOR_VERSION}"
        )[:96]

    async def cancel(self, job_id: int) -> TranslationJobRead:
        job = await self._job(job_id)
        await self._authorize_job(job)
        if job.state == "cancelled":
            return self._job_read(job)
        if job.state in {"succeeded", "failed"}:
            raise TranslationStateError("Terminal translation cannot be cancelled")
        now = datetime.now(UTC)
        job.state = "cancelled"
        job.cancel_requested_at = now
        job.finished_at = now
        task = await self._session.get(TaskRecord, job.task_id)
        if task is not None:
            task.status = "cancelled"
            task.phase = "cancelled"
            task.active_idempotency_key = None
            task.lease_owner = None
            task.lease_expires_at = None
            task.finished_at = now
        await self._session.flush()
        return self._job_read(job)

    async def retry(self, job_id: int) -> TranslationJobRead:
        original = await self._job(job_id)
        await self._authorize_job(original)
        if original.state not in {"failed", "cancelled"}:
            raise TranslationStateError(
                "Only failed or cancelled translations can be retried"
            )
        return await self.create_job(
            original.document_id,
            TranslationJobCreate(
                source_anchor_id=original.source_anchor_id,
                source_language=original.source_language,
                target_language=original.target_language,
            ),
            f"retry-{original.id}-{uuid4().hex}",
        )

    async def correct(
        self, revision_id: int, payload: TranslationCorrectionCreate
    ) -> TranslationRevisionRead:
        base = await self._session.get(TranslationRevision, revision_id)
        if base is None:
            raise NotFoundError("Translation revision not found")
        await SourceAnchorService(self._session).get(
            base.source_anchor_id, base.document_id
        )
        root_id = base.root_revision_id or base.id
        latest_version = await self._session.scalar(
            select(func.max(TranslationRevision.version)).where(
                (TranslationRevision.id == root_id)
                | (TranslationRevision.root_revision_id == root_id)
            )
        )
        if (
            latest_version != payload.expected_version
            or base.version != payload.expected_version
        ):
            raise TranslationConflictError("Translation revision has changed")
        report = validate_translation(
            (
                await self._session.get(DocumentSourceAnchor, base.source_anchor_id)
            ).quote,  # type: ignore[union-attr]
            payload.translated_text,
        )
        corrected = TranslationRevision(
            document_id=base.document_id,
            source_anchor_id=base.source_anchor_id,
            anchor_revision_id=base.anchor_revision_id,
            segmentation_revision_id=base.segmentation_revision_id,
            root_revision_id=root_id,
            supersedes_revision_id=base.id,
            version=base.version + 1,
            origin="human",
            source_text_hash=base.source_text_hash,
            source_language=base.source_language,
            target_language=base.target_language,
            translated_text=payload.translated_text.strip(),
            alignment_json=base.alignment_json,
            terminology_json=json.dumps(
                [asdict(term) for term in report.terms], ensure_ascii=False
            ),
            quality_status="human_reviewed",
            provider="human",
            model="human-correction",
            model_revision="local",
            prompt_version=base.prompt_version,
            config_version=base.config_version,
            policy_version=base.policy_version,
            terminology_version=base.terminology_version,
            validator_version=VALIDATOR_VERSION,
            context_hash=base.context_hash,
        )
        self._session.add(corrected)
        await self._session.flush()
        validation = TranslationValidationReport(
            revision_id=corrected.id,
            validator_version=VALIDATOR_VERSION,
            issues_json=json.dumps(
                [asdict(issue) for issue in report.issues], ensure_ascii=False
            ),
            deterministic_passed=0 if report.blocked else 1,
            highest_severity=_highest_severity(report.issues),
        )
        self._session.add(validation)
        await self._session.flush()
        self._session.add(
            TranslationReview(
                base_revision_id=base.id,
                corrected_revision_id=corrected.id,
                expected_version=payload.expected_version,
                reason=payload.reason,
            )
        )
        await self._session.flush()
        return await self.revision_read(corrected)

    async def save_term_override(
        self, document_id: int, payload: TranslationTermOverrideCreate
    ) -> TranslationTermOverrideRead:
        # The document's anchor/document access boundary applies here; this
        # endpoint intentionally stores no cross-document or global term state.
        await AnchorQueries(self._session).authorized_document(document_id)
        normalized = payload.source_term.strip().casefold()
        existing = await self._session.scalar(
            select(TranslationTermOverride).where(
                TranslationTermOverride.document_id == document_id,
                TranslationTermOverride.normalized_source_term == normalized,
                TranslationTermOverride.target_language == payload.target_language,
            )
        )
        now = datetime.now(UTC)
        if existing is None:
            existing = TranslationTermOverride(
                document_id=document_id,
                source_term=payload.source_term.strip(),
                normalized_source_term=normalized,
                target_term=payload.target_term.strip(),
                target_language=payload.target_language,
                scope="document",
                updated_at=now,
            )
            self._session.add(existing)
        else:
            existing.source_term = payload.source_term.strip()
            existing.target_term = payload.target_term.strip()
            existing.updated_at = now
        await self._session.flush()
        return self._term_override_read(existing)

    async def list_term_overrides(
        self, document_id: int, target_language: str = "zh-CN"
    ) -> list[TranslationTermOverrideRead]:
        await AnchorQueries(self._session).authorized_document(document_id)
        rows = list(
            (
                await self._session.scalars(
                    select(TranslationTermOverride)
                    .where(
                        TranslationTermOverride.document_id == document_id,
                        TranslationTermOverride.target_language == target_language,
                    )
                    .order_by(TranslationTermOverride.source_term)
                )
            ).all()
        )
        return [self._term_override_read(row) for row in rows]

    async def revision_read(
        self, revision: TranslationRevision
    ) -> TranslationRevisionRead:
        validation = await self._session.scalar(
            select(TranslationValidationReport).where(
                TranslationValidationReport.revision_id == revision.id
            )
        )
        return TranslationRevisionRead(
            id=revision.id,
            document_id=revision.document_id,
            source_anchor_id=revision.source_anchor_id,
            version=revision.version,
            origin=revision.origin,
            source_language=revision.source_language,
            target_language=revision.target_language,
            translated_text=revision.translated_text,
            alignment=json.loads(revision.alignment_json),
            terms=json.loads(revision.terminology_json),
            issues=json.loads(validation.issues_json) if validation else [],
            quality_status=revision.quality_status,  # type: ignore[arg-type]
            provider=revision.provider,
            model=revision.model,
            created_at=revision.created_at,
        )

    async def _job(self, job_id: int) -> MedicalTranslationJob:
        job = await self._session.get(MedicalTranslationJob, job_id)
        if job is None:
            raise NotFoundError("Translation job not found")
        return job

    async def _authorize_job(self, job: MedicalTranslationJob) -> None:
        await SourceAnchorService(self._session).get(
            job.source_anchor_id, job.document_id
        )

    @staticmethod
    def _job_read(job: MedicalTranslationJob) -> TranslationJobRead:
        return TranslationJobRead.model_validate(job, from_attributes=True)

    @staticmethod
    def _term_override_read(
        override: TranslationTermOverride,
    ) -> TranslationTermOverrideRead:
        return TranslationTermOverrideRead.model_validate(
            override, from_attributes=True
        )


def _highest_severity(issues: tuple[QualityIssue, ...]) -> str | None:
    order = {"info": 0, "warning": 1, "error": 2, "critical": 3}
    severities = [issue.severity for issue in issues]
    return max(severities, key=order.__getitem__) if severities else None
