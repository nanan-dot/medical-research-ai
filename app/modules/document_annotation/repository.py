"""批注持久化访问。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_annotation.model import DocumentAnnotation


class DocumentAnnotationRepository:
    """只访问批注表，文档版本判断留给服务层。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_active(self, document_id: int) -> list[DocumentAnnotation]:
        result = await self._session.execute(
            select(DocumentAnnotation)
            .where(
                DocumentAnnotation.document_id == document_id,
                DocumentAnnotation.deleted_at.is_(None),
            )
            .order_by(DocumentAnnotation.page_number, DocumentAnnotation.id)
        )
        return list(result.scalars().all())

    async def get_active(
        self,
        document_id: int,
        annotation_id: int,
    ) -> DocumentAnnotation | None:
        result = await self._session.execute(
            select(DocumentAnnotation).where(
                DocumentAnnotation.id == annotation_id,
                DocumentAnnotation.document_id == document_id,
                DocumentAnnotation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, annotation: DocumentAnnotation) -> DocumentAnnotation:
        self._session.add(annotation)
        await self._session.flush()
        await self._session.refresh(annotation)
        return annotation

    async def save(self, annotation: DocumentAnnotation) -> DocumentAnnotation:
        await self._session.flush()
        await self._session.refresh(annotation)
        return annotation
