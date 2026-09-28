"""Generate relocation evidence and apply explicit human decisions."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
    DocumentSourcePage,
    DocumentSourceTextItem,
)
from app.modules.document_anchor.queries import AnchorQueries
from app.modules.document_anchor.selection_ranges import utf16_length
from app.modules.document_layout.model import DocumentSegmentationRevision
from app.modules.document_relocation.errors import RelocationError
from app.modules.document_relocation.model import (
    AssetAnchorLink,
    DocumentAnchorRelocation,
    DocumentAnchorRelocationDecision,
)
from app.modules.document_relocation.schema import (
    AssetResolutionRead,
    CandidateRead,
    DecisionCreate,
    ResolutionIssueRead,
)
from app.modules.document_relocation.scoring import score_candidate
from app.modules.document_selection.schema import (
    SelectionFragment,
    SourceAnchorDescriptor,
)
from app.modules.document_selection.service import SourceAnchorService

ALGORITHM_VERSION = "a3-relocation-1"
MAX_CANDIDATES = 10


class RelocationService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._anchors = SourceAnchorService(session)

    async def generate(
        self, source_anchor_id: int, target_revision_id: int
    ) -> list[CandidateRead]:
        source = await self._source(source_anchor_id)
        target = await self._session.get(DocumentAnchorRevision, target_revision_id)
        if target is None or target.document_id != source[1].document_id:
            raise RelocationError("RELOCATION_TARGET_REVISION_STALE")
        document = await AnchorQueries(self._session).authorized_document(
            target.document_id, fresh=True
        )
        if (
            target.state not in {"ready", "review_required"}
            or document.file_hash != target.file_hash
        ):
            raise RelocationError("RELOCATION_TARGET_REVISION_STALE")
        layout = await self._session.scalar(
            select(DocumentSegmentationRevision)
            .where(
                DocumentSegmentationRevision.anchor_revision_id == target.id,
                DocumentSegmentationRevision.state.in_(("ready", "review_required")),
            )
            .order_by(DocumentSegmentationRevision.id.desc())
        )
        if layout is None:
            raise RelocationError("RELOCATION_TARGET_REVISION_STALE")
        rows = (
            await self._session.execute(
                select(DocumentSourceTextItem, DocumentSourcePage.page_number)
                .join(
                    DocumentSourcePage,
                    DocumentSourcePage.id == DocumentSourceTextItem.page_id,
                )
                .where(DocumentSourcePage.revision_id == target.id)
                .order_by(
                    DocumentSourcePage.page_number, DocumentSourceTextItem.item_index
                )
            )
        ).all()
        created: list[DocumentAnchorRelocation] = []
        for item, page_number in rows:
            start = 0
            while len(created) < MAX_CANDIDATES:
                index = item.raw_text.find(source[0].quote, start)
                if index < 0:
                    break
                prefix = item.raw_text[:index]
                selected = item.raw_text[index : index + len(source[0].quote)]
                descriptor = SourceAnchorDescriptor(
                    expected_file_hash=target.file_hash,
                    expected_anchor_revision_id=target.id,
                    expected_segmentation_revision_id=layout.id,
                    browser_quote=selected,
                    fragments=[
                        SelectionFragment(
                            page_number=page_number,
                            start_item_index=item.item_index,
                            end_item_index=item.item_index,
                            start_offset_utf16=utf16_length(prefix),
                            end_offset_utf16=utf16_length(prefix + selected),
                            rectangles=[],
                        )
                    ],
                )
                candidate = await self._anchors.create(target.document_id, descriptor)
                score = score_candidate(source[0].quote, candidate.quote)
                relocation = await self._existing(
                    source_anchor_id, target.id, candidate.id
                )
                if relocation is None:
                    relocation = DocumentAnchorRelocation(
                        source_anchor_id=source_anchor_id,
                        target_anchor_revision_id=target.id,
                        candidate_anchor_id=candidate.id,
                        method="quote_exact",
                        algorithm_version=ALGORITHM_VERSION,
                        score_breakdown_json=json.dumps(
                            score.breakdown, separators=(",", ":")
                        ),
                        protected_token_status=score.protected_token_status,
                        status="proposed",
                    )
                    self._session.add(relocation)
                    await self._session.flush()
                created.append(relocation)
                start = index + max(1, len(selected))
        if not created:
            for item, page_number in rows:
                score = score_candidate(source[0].quote, item.raw_text)
                if score.breakdown["quote_exactness"] < 0.45:
                    continue
                descriptor = SourceAnchorDescriptor(
                    expected_file_hash=target.file_hash,
                    expected_anchor_revision_id=target.id,
                    expected_segmentation_revision_id=layout.id,
                    browser_quote=item.raw_text,
                    fragments=[
                        SelectionFragment(
                            page_number=page_number,
                            start_item_index=item.item_index,
                            end_item_index=item.item_index,
                            start_offset_utf16=0,
                            end_offset_utf16=utf16_length(item.raw_text),
                            rectangles=[],
                        )
                    ],
                )
                candidate = await self._anchors.create(target.document_id, descriptor)
                relocation = await self._existing(
                    source_anchor_id, target.id, candidate.id
                )
                if relocation is None:
                    relocation = DocumentAnchorRelocation(
                        source_anchor_id=source_anchor_id,
                        target_anchor_revision_id=target.id,
                        candidate_anchor_id=candidate.id,
                        method="quote_approximate",
                        algorithm_version=ALGORITHM_VERSION,
                        score_breakdown_json=json.dumps(
                            score.breakdown, separators=(",", ":")
                        ),
                        protected_token_status=score.protected_token_status,
                        status="proposed",
                    )
                    self._session.add(relocation)
                    await self._session.flush()
                created.append(relocation)
                if len(created) == MAX_CANDIDATES:
                    break
        if not created:
            raise RelocationError("RELOCATION_NO_CANDIDATE")
        uniqueness = 1.0 if len(created) == 1 else 0.0
        for row in created:
            breakdown = json.loads(row.score_breakdown_json)
            breakdown["candidate_uniqueness"] = uniqueness
            row.score_breakdown_json = json.dumps(breakdown, separators=(",", ":"))
        return [self._read(row) for row in created]

    async def list_candidates(self, source_anchor_id: int) -> list[CandidateRead]:
        await self._source(source_anchor_id)
        rows = list(
            (
                await self._session.scalars(
                    select(DocumentAnchorRelocation)
                    .where(
                        DocumentAnchorRelocation.source_anchor_id == source_anchor_id
                    )
                    .order_by(DocumentAnchorRelocation.id)
                )
            ).all()
        )
        return [self._read(row) for row in rows]

    async def issues(self, document_id: int) -> list[ResolutionIssueRead]:
        await AnchorQueries(self._session).authorized_document(document_id, fresh=True)
        rows = (
            await self._session.execute(
                select(AssetAnchorLink, func.count(DocumentAnchorRelocation.id))
                .join(
                    DocumentSourceAnchor,
                    DocumentSourceAnchor.id == AssetAnchorLink.original_anchor_id,
                )
                .join(
                    DocumentAnchorRevision,
                    DocumentAnchorRevision.id
                    == DocumentSourceAnchor.anchor_revision_id,
                )
                .outerjoin(
                    DocumentAnchorRelocation,
                    DocumentAnchorRelocation.source_anchor_id
                    == AssetAnchorLink.original_anchor_id,
                )
                .where(
                    DocumentAnchorRevision.document_id == document_id,
                    AssetAnchorLink.resolution_status.in_(
                        ("relocation_required", "relocated_unverified")
                    ),
                )
                .group_by(AssetAnchorLink.id)
                .order_by(AssetAnchorLink.id)
            )
        ).all()
        return [
            ResolutionIssueRead(
                asset_type=link.asset_type,
                asset_id=link.asset_id,
                original_anchor_id=link.original_anchor_id,
                resolved_anchor_id=link.resolved_anchor_id,
                resolution_status=link.resolution_status,
                resolution_version=link.resolution_version,
                candidate_count=count,
            )
            for link, count in rows
        ]

    async def decide(
        self, source_anchor_id: int, relocation_id: int, payload: DecisionCreate
    ) -> AssetResolutionRead:
        if payload.candidate_id != relocation_id:
            raise RelocationError("RELOCATION_CANDIDATE_MISMATCH")
        await self._source(source_anchor_id)
        relocation = await self._session.get(DocumentAnchorRelocation, relocation_id)
        if relocation is None or relocation.source_anchor_id != source_anchor_id:
            raise NotFoundError("Relocation candidate not found")
        link = await self._session.scalar(
            select(AssetAnchorLink).where(
                AssetAnchorLink.asset_type == payload.asset_type,
                AssetAnchorLink.asset_id == payload.asset_id,
            )
        )
        if link is None or link.original_anchor_id != source_anchor_id:
            raise RelocationError("ASSET_ANCHOR_MISMATCH")
        await self._session.execute(
            update(AssetAnchorLink)
            .where(AssetAnchorLink.id == link.id)
            .values(resolution_version=AssetAnchorLink.resolution_version)
        )
        await self._session.refresh(link)
        if link.resolution_version != payload.expected_resolution_version:
            raise RelocationError("RESOLUTION_VERSION_CONFLICT")
        previous_version = link.resolution_version
        if payload.decision == "confirm":
            if (
                relocation.candidate_anchor_id is None
                or relocation.protected_token_status != "match"
            ):
                raise RelocationError("RELOCATION_PROTECTED_TOKEN_MISMATCH")
            candidate_anchor = await self._session.get(
                DocumentSourceAnchor, relocation.candidate_anchor_id
            )
            candidate_revision = (
                await self._session.get(
                    DocumentAnchorRevision, candidate_anchor.anchor_revision_id
                )
                if candidate_anchor is not None
                else None
            )
            document = (
                await AnchorQueries(self._session).authorized_document(
                    candidate_revision.document_id, fresh=True
                )
                if candidate_revision is not None
                else None
            )
            if (
                candidate_revision is None
                or candidate_revision.id != relocation.target_anchor_revision_id
                or candidate_revision.state not in {"ready", "review_required"}
                or document is None
                or document.file_hash != candidate_revision.file_hash
            ):
                raise RelocationError("RELOCATION_TARGET_REVISION_STALE")
            await self._session.execute(
                update(DocumentAnchorRelocation)
                .where(
                    DocumentAnchorRelocation.source_anchor_id == source_anchor_id,
                    DocumentAnchorRelocation.status == "confirmed",
                    DocumentAnchorRelocation.id != relocation.id,
                )
                .values(status="superseded")
            )
            relocation.status = "confirmed"
            link.resolved_anchor_id = relocation.candidate_anchor_id
            link.resolution_status = "relocated_verified"
        elif payload.decision == "reject":
            relocation.status = "rejected"
        else:
            relocation.status = "superseded"
            link.resolved_anchor_id = None
            link.resolution_status = "relocation_required"
        relocation.decision_source = "human"
        relocation.reviewer_id = "local_user"
        relocation.reviewed_at = datetime.now(UTC)
        relocation.decision_note = payload.decision_note
        link.resolution_version += 1
        self._session.add(
            DocumentAnchorRelocationDecision(
                relocation_id=relocation.id,
                decision=payload.decision,
                decision_source="human",
                reviewer_id="local_user",
                decision_note=payload.decision_note,
                previous_resolution_version=previous_version,
                resulting_resolution_version=link.resolution_version,
            )
        )
        await self._session.flush()
        return self._link_read(link)

    async def _source(
        self, anchor_id: int
    ) -> tuple[DocumentSourceAnchor, DocumentAnchorRevision]:
        anchor = await self._session.get(DocumentSourceAnchor, anchor_id)
        if anchor is None:
            raise NotFoundError("Source anchor not found")
        revision = await self._session.get(
            DocumentAnchorRevision, anchor.anchor_revision_id
        )
        if revision is None:
            raise NotFoundError("Source revision not found")
        await AnchorQueries(self._session).authorized_document(
            revision.document_id, fresh=True
        )
        return anchor, revision

    async def _existing(
        self, source_id: int, target_id: int, candidate_id: int
    ) -> DocumentAnchorRelocation | None:
        return await self._session.scalar(
            select(DocumentAnchorRelocation).where(
                DocumentAnchorRelocation.source_anchor_id == source_id,
                DocumentAnchorRelocation.target_anchor_revision_id == target_id,
                DocumentAnchorRelocation.candidate_anchor_id == candidate_id,
                DocumentAnchorRelocation.algorithm_version == ALGORITHM_VERSION,
            )
        )

    @staticmethod
    def _read(row: DocumentAnchorRelocation) -> CandidateRead:
        return CandidateRead(
            id=row.id,
            source_anchor_id=row.source_anchor_id,
            target_anchor_revision_id=row.target_anchor_revision_id,
            candidate_anchor_id=row.candidate_anchor_id,
            method=row.method,
            algorithm_version=row.algorithm_version,
            score_breakdown=json.loads(row.score_breakdown_json),
            protected_token_status=row.protected_token_status,
            status=row.status,
            decision_source=row.decision_source,
            created_at=row.created_at,
        )

    @staticmethod
    def _link_read(link: AssetAnchorLink) -> AssetResolutionRead:
        return AssetResolutionRead(
            asset_type=link.asset_type,
            asset_id=link.asset_id,
            original_anchor_id=link.original_anchor_id,
            resolved_anchor_id=link.resolved_anchor_id,
            resolution_status=link.resolution_status,
            resolution_version=link.resolution_version,
        )


__all__ = ["RelocationService"]
