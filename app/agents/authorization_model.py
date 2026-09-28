"""模型内容外发授权。"""

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelTransferAuthorizationRecord(Base):
    __tablename__ = "model_transfer_authorizations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active','revoked','expired','consumed')",
            name="ck_model_authorization_status",
        ),
        CheckConstraint(
            "payload_shape IN ('single_item','multi_item_bundle')",
            name="ck_model_authorization_payload_shape",
        ),
        CheckConstraint(
            "content_transform IN ('raw','deidentified','aggregated')",
            name="ck_model_authorization_content_transform",
        ),
        CheckConstraint(
            "revision >= 1", name="ck_model_authorization_revision_positive"
        ),
    )

    authorization_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    research_context_id: Mapped[str] = mapped_column(String(64), index=True)
    actor_scope: Mapped[str] = mapped_column(String(128))
    provider_scope: Mapped[str] = mapped_column(String(128))
    model_scope: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[str] = mapped_column(String(128))
    content_granularity: Mapped[str] = mapped_column(String(32))
    data_categories_json: Mapped[list[str]] = mapped_column(JSON)
    payload_refs_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    payload_hash: Mapped[str] = mapped_column(String(64))
    payload_shape: Mapped[str] = mapped_column(String(32))
    content_transform: Mapped[str] = mapped_column(String(32))
    allow_cloud_transfer: Mapped[bool] = mapped_column(default=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
