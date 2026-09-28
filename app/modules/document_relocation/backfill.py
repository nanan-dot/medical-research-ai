"""Auditable, idempotent legacy asset backfill with dry-run isolation."""

import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError, PermissionDeniedError
from app.modules.conversation.model import Citation
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_anchor.selection_ranges import utf16_length
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_layout.model import (
    DocumentLayoutBlock,
    DocumentSegmentationRevision,
)
from app.modules.document_relocation.errors import RelocationError
from app.modules.document_relocation.model import (
    AssetAnchorLink,
    LegacyAnchorBackfillItem,
    LegacyAnchorBackfillRun,
)
from app.modules.document_relocation.schema import BackfillRunCreate, BackfillRunRead
from app.modules.document_selection.errors import SelectionError
from app.modules.document_selection.schema import (
    SelectionFragment,
    SelectionRect,
    SourceAnchorDescriptor,
)
from app.modules.document_selection.service import SourceAnchorService
from app.modules.task.model import TaskRecord

BACKFILL_VERSION = "a3-backfill-1"
BATCH_SIZE = 100


class BackfillService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self, payload: BackfillRunCreate, *, is_admin: bool
    ) -> BackfillRunRead:
        if payload.mode == "apply" and not is_admin:
            raise PermissionDeniedError(
                "Apply backfill requires an explicit local admin operation"
            )
        target = await self._target(payload.target_anchor_revision_id)
        existing = await self._session.scalar(
            select(LegacyAnchorBackfillRun)
            .where(
                LegacyAnchorBackfillRun.asset_type == payload.asset_type,
                LegacyAnchorBackfillRun.source_schema_version
                == payload.source_schema_version,
                LegacyAnchorBackfillRun.target_anchor_revision_id == target.id,
                LegacyAnchorBackfillRun.algorithm_version == BACKFILL_VERSION,
                LegacyAnchorBackfillRun.mode == payload.mode,
            )
            .order_by(LegacyAnchorBackfillRun.id.desc())
        )
        if existing is not None:
            if existing.status == "running":
                task = await self._session.get(TaskRecord, existing.task_id)
                if task is not None:
                    await self._execute(existing, target, task)
            return self._read(existing)
        run = LegacyAnchorBackfillRun(
            asset_type=payload.asset_type,
            source_schema_version=payload.source_schema_version,
            target_anchor_revision_id=target.id,
            mode=payload.mode,
            algorithm_version=BACKFILL_VERSION,
            status="running",
        )
        self._session.add(run)
        await self._session.flush()
        task = TaskRecord(
            task_type="legacy_anchor_backfill",
            title="旧原文资产锚点回填",
            status="running",
            phase="matching",
            source_type="legacy_anchor_backfill_run",
            source_id=run.id,
            detail_json=json.dumps({"run_id": run.id, "mode": run.mode}),
        )
        self._session.add(task)
        await self._session.flush()
        run.task_id = task.id
        await self._execute(run, target, task)
        return self._read(run)

    async def _execute(
        self,
        run: LegacyAnchorBackfillRun,
        target: DocumentAnchorRevision,
        task: TaskRecord,
    ) -> None:
        if run.asset_type == "document_annotation":
            await self._annotations(run, target)
        else:
            await self._citations(run, target)
        if run.status == "cancelled":
            return
        run.status = "completed"
        run.finished_at = datetime.now(UTC)
        task.status = "succeeded"
        task.phase = "completed"
        task.progress = 100
        task.completed_units = run.scanned
        task.total_units = run.total
        task.finished_at = run.finished_at
        run.report_json = json.dumps(
            {
                "counts": {
                    "total": run.total,
                    "exact": run.exact,
                    "candidate": run.candidate,
                    "unresolved": run.unresolved,
                    "failed": run.failed,
                }
            },
            separators=(",", ":"),
        )
        await self._session.flush()

    async def get(self, run_id: int) -> BackfillRunRead:
        run = await self._session.get(LegacyAnchorBackfillRun, run_id)
        if run is None:
            raise NotFoundError("Backfill run not found")
        await self._target(run.target_anchor_revision_id)
        return self._read(run)

    async def cancel(self, run_id: int) -> BackfillRunRead:
        run = await self._session.get(LegacyAnchorBackfillRun, run_id)
        if run is None:
            raise NotFoundError("Backfill run not found")
        await self._target(run.target_anchor_revision_id)
        if run.status in {"pending", "running"}:
            run.status = "cancelled"
            run.finished_at = datetime.now(UTC)
        return self._read(run)

    async def _target(self, revision_id: int | None) -> DocumentAnchorRevision:
        target = await self._session.get(DocumentAnchorRevision, revision_id)
        if target is None:
            raise RelocationError("LEGACY_SOURCE_REVISION_MISSING")
        document = await AnchorQueries(self._session).authorized_document(
            target.document_id, fresh=True
        )
        if (
            target.state not in {"ready", "review_required"}
            or document.file_hash != target.file_hash
        ):
            raise RelocationError("RELOCATION_TARGET_REVISION_STALE")
        return target

    async def _annotations(
        self, run: LegacyAnchorBackfillRun, target: DocumentAnchorRevision
    ) -> None:
        if run.scanned == 0:
            run.total = int(
                await self._session.scalar(
                    select(func.count())
                    .select_from(DocumentAnnotation)
                    .where(
                        DocumentAnnotation.document_id == target.document_id,
                        DocumentAnnotation.source_anchor_id.is_(None),
                        DocumentAnnotation.deleted_at.is_(None),
                    )
                )
                or 0
            )
        while run.status == "running":
            cursor = int(run.cursor or 0)
            rows = list(
                (
                    await self._session.scalars(
                        select(DocumentAnnotation)
                        .where(
                            DocumentAnnotation.document_id == target.document_id,
                            DocumentAnnotation.source_anchor_id.is_(None),
                            DocumentAnnotation.deleted_at.is_(None),
                            DocumentAnnotation.id > cursor,
                        )
                        .order_by(DocumentAnnotation.id)
                        .limit(BATCH_SIZE)
                    )
                ).all()
            )
            if not rows:
                break
            for annotation in rows:
                await self._annotation_item(run, target, annotation)
            await self._session.commit()
            await self._session.refresh(run)

    async def _annotation_item(
        self,
        run: LegacyAnchorBackfillRun,
        target: DocumentAnchorRevision,
        annotation: DocumentAnnotation,
    ) -> None:
        run.scanned += 1
        run.cursor = str(annotation.id)
        try:
            async with self._session.begin_nested():
                (
                    status,
                    anchor_id,
                    candidate_count,
                    reasons,
                ) = await self._match_annotation(annotation, target, run.mode)
        except (ValueError, json.JSONDecodeError, SelectionError):
            status, anchor_id, candidate_count, reasons = (
                "failed",
                None,
                0,
                ["LEGACY_ITEM_INVALID"],
            )
        setattr(run, status, getattr(run, status) + 1)
        self._session.add(
            LegacyAnchorBackfillItem(
                run_id=run.id,
                asset_type="document_annotation",
                asset_id=annotation.id,
                legacy_identity_hash=self._identity(
                    annotation.id, annotation.selected_text_hash
                ),
                result_status=status,
                anchor_id=anchor_id,
                candidate_count=candidate_count,
                reason_codes_json=json.dumps(reasons),
                error_code="LEGACY_ITEM_INVALID" if status == "failed" else None,
            )
        )

    async def _match_annotation(
        self, annotation: DocumentAnnotation, target: DocumentAnchorRevision, mode: str
    ) -> tuple[str, int | None, int, list[str]]:
        if annotation.file_hash != target.file_hash:
            return "unresolved", None, 0, ["LEGACY_SOURCE_REVISION_MISSING"]
        if hashlib.sha256(annotation.selected_text.encode("utf-8")).hexdigest() != annotation.selected_text_hash:
            return "unresolved", None, 0, ["LEGACY_TEXT_HASH_MISMATCH"]
        layout = await self._session.scalar(
            select(DocumentSegmentationRevision).where(
                DocumentSegmentationRevision.anchor_revision_id == target.id,
                DocumentSegmentationRevision.state.in_(("ready", "review_required")),
            )
        )
        if layout is None:
            return "unresolved", None, 0, ["SEGMENTATION_MISSING"]
        page = await self._session.scalar(
            select(DocumentSourcePage).where(
                DocumentSourcePage.revision_id == target.id,
                DocumentSourcePage.page_number == annotation.page_number,
            )
        )
        if page is None:
            return "unresolved", None, 0, ["PAGE_MISSING"]
        items = list(
            (
                await self._session.scalars(
                    select(DocumentSourceTextItem)
                    .where(DocumentSourceTextItem.page_id == page.id)
                    .order_by(DocumentSourceTextItem.item_index)
                )
            ).all()
        )
        blocks = list(
            (
                await self._session.scalars(
                    select(DocumentLayoutBlock).where(
                        DocumentLayoutBlock.segmentation_revision_id == layout.id,
                        DocumentLayoutBlock.page_id == page.id,
                    )
                )
            ).all()
        )
        legacy_rectangles = [
            SelectionRect.model_validate(rect)
            for rect in json.loads(annotation.selection_geometry)
        ]
        candidates: list[SourceAnchorDescriptor] = []
        for item in items:
            start = 0
            while True:
                index = item.raw_text.find(annotation.selected_text, start)
                if index < 0:
                    break
                block = next(
                    (
                        row
                        for row in blocks
                        if item.item_index in json.loads(row.item_indexes_json)
                    ),
                    None,
                )
                if block is not None and self._geometry_matches(
                    legacy_rectangles, json.loads(block.bbox_json)
                ):
                    prefix = item.raw_text[:index]
                    selected = item.raw_text[
                        index : index + len(annotation.selected_text)
                    ]
                    candidates.append(
                        SourceAnchorDescriptor(
                            expected_file_hash=target.file_hash,
                            expected_anchor_revision_id=target.id,
                            expected_segmentation_revision_id=layout.id,
                            browser_quote=selected,
                            fragments=[
                                SelectionFragment(
                                    page_number=page.page_number,
                                    start_item_index=item.item_index,
                                    end_item_index=item.item_index,
                                    start_offset_utf16=utf16_length(prefix),
                                    end_offset_utf16=utf16_length(prefix + selected),
                                    rectangles=legacy_rectangles,
                                )
                            ],
                        )
                    )
                start = index + max(1, len(annotation.selected_text))
        if len(candidates) != 1:
            return (
                ("candidate" if candidates else "unresolved"),
                None,
                len(candidates),
                ["AMBIGUOUS" if candidates else "NO_MATCH"],
            )
        if mode == "dry_run":
            return "exact", None, 1, []
        anchor = await SourceAnchorService(self._session).create(
            target.document_id, candidates[0]
        )
        annotation.source_anchor_id = anchor.id
        self._session.add(
            AssetAnchorLink(
                asset_type="document_annotation",
                asset_id=annotation.id,
                original_anchor_id=anchor.id,
                resolved_anchor_id=anchor.id,
                resolution_status="anchored_exact",
                resolution_version=1,
            )
        )
        return "exact", anchor.id, 1, []

    async def _citations(
        self, run: LegacyAnchorBackfillRun, target: DocumentAnchorRevision
    ) -> None:
        rows = list(
            (
                await self._session.scalars(
                    select(Citation)
                    .where(
                        Citation.document_id == target.document_id,
                        Citation.source_anchor_id.is_(None),
                    )
                    .order_by(Citation.id)
                )
            ).all()
        )
        run.total = len(rows)
        for citation in rows:
            run.scanned += 1
            run.cursor = str(citation.id)
            run.candidate += 1 if citation.evidence_text else 0
            run.unresolved += 0 if citation.evidence_text else 1
            citation.anchor_status = "legacy_unversioned"
            self._session.add(
                LegacyAnchorBackfillItem(
                    run_id=run.id,
                    asset_type="citation",
                    asset_id=citation.id,
                    legacy_identity_hash=self._identity(
                        citation.id, citation.evidence_text or ""
                    ),
                    result_status="candidate"
                    if citation.evidence_text
                    else "unresolved",
                    anchor_id=None,
                    candidate_count=0,
                    reason_codes_json='["LEGACY_ASSET_UNVERSIONED"]',
                )
            )

    @staticmethod
    def _geometry_matches(rectangles: list[SelectionRect], block: list[float]) -> bool:
        if not rectangles or len(block) != 4:
            return False
        left, top, width, height = block
        rect = rectangles[0]
        center_distance = abs((rect.left + rect.width / 2) - (left + width / 2)) + abs(
            (rect.top + rect.height / 2) - (top + height / 2)
        )
        return center_distance <= 0.05

    @staticmethod
    def _identity(asset_id: int, evidence: str) -> str:
        return hashlib.sha256(f"{asset_id}:{evidence}".encode()).hexdigest()

    @staticmethod
    def _read(run: LegacyAnchorBackfillRun) -> BackfillRunRead:
        return BackfillRunRead.model_validate(run, from_attributes=True)


__all__ = ["BackfillService"]
