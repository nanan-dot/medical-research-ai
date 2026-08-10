"""单 PDF 上传接口模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.document.schema import DocumentRead


class DocumentAssetRead(BaseModel):
    """上传完成后返回的原始资产元数据。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_kind: str
    original_filename: str
    stored_relative_path: str
    media_type: str
    byte_size: int
    sha256: str
    processing_status: str
    created_at: datetime


class DocumentUploadRead(BaseModel):
    """单文件上传成功响应。"""

    document: DocumentRead
    asset: DocumentAssetRead
    auto_parse_started: bool = False
    parse_trigger_url: str
