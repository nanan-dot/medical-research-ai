"""HTTP entry point for evidence-bound local document navigation."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.modules.document_navigation.schema import DocumentNavigationRequest, DocumentNavigationResponse
from app.modules.document_navigation.service import DocumentNavigationService

router = APIRouter(prefix="/document-navigation", tags=["文档导航"])


@router.post("/search", response_model=DocumentNavigationResponse)
async def search_documents(
    request: DocumentNavigationRequest,
    session: AsyncSession = Depends(get_session),
) -> DocumentNavigationResponse:
    return await DocumentNavigationService(session).search(request)
