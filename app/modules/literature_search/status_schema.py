from datetime import datetime

from pydantic import BaseModel

from app.modules.literature_search.status_classifier import Status


class LiteratureStatusRequest(BaseModel):
    verified: bool = False
    is_retracted: bool = False
    is_corrected: bool = False
    is_preprint: bool = False
class LiteratureStatusRead(BaseModel):
    status: Status
    persistent: bool = False
    checked_at: datetime | None = None
class LiteratureStatusPersistRequest(LiteratureStatusRequest):
    document_id: int
    source: str
    notice_url_or_id: str | None = None
