"""A3 relocation candidate and explicit decision endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_relocation.backfill import BackfillService
from app.modules.document_relocation.schema import (
    AssetResolutionRead,
    BackfillRunCreate,
    BackfillRunRead,
    CandidateRead,
    CandidateRequest,
    DecisionCreate,
    ResolutionIssueRead,
)
from app.modules.document_relocation.service import RelocationService

router = APIRouter(tags=["source-anchor-relocations"])
Session = Annotated[AsyncSession, Depends(get_session)]


@router.get(
    "/documents/{document_id}/anchor-resolution-issues",
    response_model=list[ResolutionIssueRead],
)
async def list_resolution_issues(
    document_id: int, session: Session
) -> list[ResolutionIssueRead]:
    return await RelocationService(session).issues(document_id)


@router.post(
    "/document-anchors/backfill-runs", response_model=BackfillRunRead, status_code=201
)
async def create_backfill_run(
    payload: BackfillRunCreate,
    session: Session,
    admin_operation: Annotated[str | None, Header(alias="X-Admin-Operation")] = None,
) -> BackfillRunRead:
    return await BackfillService(session).create(
        payload, is_admin=admin_operation == "confirm"
    )


@router.get("/document-anchors/backfill-runs/{run_id}", response_model=BackfillRunRead)
async def read_backfill_run(run_id: int, session: Session) -> BackfillRunRead:
    return await BackfillService(session).get(run_id)


@router.get(
    "/document-anchors/backfill-runs/{run_id}/report", response_model=BackfillRunRead
)
async def read_backfill_report(run_id: int, session: Session) -> BackfillRunRead:
    return await BackfillService(session).get(run_id)


@router.post(
    "/document-anchors/backfill-runs/{run_id}/cancel", response_model=BackfillRunRead
)
async def cancel_backfill_run(run_id: int, session: Session) -> BackfillRunRead:
    return await BackfillService(session).cancel(run_id)


@router.post(
    "/source-anchors/{anchor_id}/relocation-candidates",
    response_model=list[CandidateRead],
    status_code=201,
)
async def create_candidates(
    anchor_id: int, payload: CandidateRequest, session: Session
) -> list[CandidateRead]:
    return await RelocationService(session).generate(
        anchor_id, payload.target_anchor_revision_id
    )


@router.get(
    "/source-anchors/{anchor_id}/relocation-candidates",
    response_model=list[CandidateRead],
)
async def list_candidates(anchor_id: int, session: Session) -> list[CandidateRead]:
    return await RelocationService(session).list_candidates(anchor_id)


@router.post(
    "/source-anchors/{anchor_id}/relocations/{relocation_id}/decisions",
    response_model=AssetResolutionRead,
)
async def decide_relocation(
    anchor_id: int, relocation_id: int, payload: DecisionCreate, session: Session
) -> AssetResolutionRead:
    return await RelocationService(session).decide(anchor_id, relocation_id, payload)


__all__ = ["router"]
