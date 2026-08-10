"""文档资产持久化访问。"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_upload.model import DocumentAsset


class DocumentAssetRepository:
    """仅封装文档资产的写入，事务边界由服务层统一管理。"""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, asset: DocumentAsset) -> DocumentAsset:
        self._session.add(asset)
        await self._session.flush()
        await self._session.refresh(asset)
        return asset
