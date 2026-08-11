"""单 PDF 上传 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile

from app.core.database import get_session
from app.modules.document_upload.schema import DocumentUploadRead
from app.modules.document_upload.service import (
    DocumentUploadService,
    UploadValidationError,
)

router = APIRouter(prefix="/document-uploads", tags=["document-uploads"])


@router.post("", response_model=DocumentUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_single_pdf(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DocumentUploadRead:
    """接收唯一的 multipart `file` 字段，拒绝多文件表单。"""

    form = await request.form()
    uploaded_values = form.getlist("file")
    if len(uploaded_values) != 1 or not isinstance(uploaded_values[0], UploadFile):
        raise UploadValidationError("请求必须包含唯一的 file PDF 字段")
    return await DocumentUploadService(session).upload(uploaded_values[0])
