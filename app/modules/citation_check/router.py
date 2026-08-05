"""citation_check — HTTP 路由"""

from fastapi import APIRouter

from app.modules.citation_check.schema import CitationCheckRequest, CitationCheckResult
from app.modules.citation_check.service import CitationCheckService

router = APIRouter(prefix="/citation-check", tags=["Citation check"])


@router.post("", response_model=CitationCheckResult)
async def check_citations(request: CitationCheckRequest) -> CitationCheckResult:
    return await CitationCheckService().check(request)
