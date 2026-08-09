"""HTTP entry point for evidence analysis."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.evidence_analysis.schema import (
    EvidenceAnalysisRead,
    EvidenceAnalysisRequest,
)
from app.modules.evidence_analysis.service import EvidenceAnalysisService

router = APIRouter(prefix="/evidence-analysis", tags=["热点、争议与证据缺口"])


@router.post("/analyze", response_model=EvidenceAnalysisRead)
async def analyze_evidence(
    payload: EvidenceAnalysisRequest, session: AsyncSession = Depends(get_session)
) -> EvidenceAnalysisRead:
    """Analyze one bounded evidence matrix with deterministic statistics and grounded interpretation."""
    return await EvidenceAnalysisService(session).analyze(payload)
