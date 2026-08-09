"""citation_check — HTTP 路由"""

from fastapi import APIRouter, HTTPException
from uuid import uuid4

from app.modules.citation_check.schema import (
    CitationCheckRequest,
    CitationCheckResult,
    CitationVerificationRequest,
)
from app.modules.citation_check.service import CitationCheckService

router = APIRouter(prefix="/citation-check", tags=["Citation check"])
_REPORTS: dict[str, CitationCheckResult] = {}


@router.post("", response_model=CitationCheckResult)
async def check_citations(request: CitationCheckRequest) -> CitationCheckResult:
    return await CitationCheckService().check(request)


@router.post("/verify", response_model=CitationCheckResult)
async def verify_citations(request: CitationVerificationRequest) -> CitationCheckResult:
    result = await CitationCheckService().check(request)
    report_id = uuid4().hex
    stored = result.model_copy(update={"report_id": report_id})
    _REPORTS[report_id] = stored
    return stored


@router.get("/reports/{report_id}", response_model=CitationCheckResult)
async def get_report(report_id: str) -> CitationCheckResult:
    report = _REPORTS.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Citation report not found")
    return report
