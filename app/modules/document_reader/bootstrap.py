"""启动快照只读编排。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.modules.document.model import Document
from app.modules.document_anchor.model import DocumentAnchorRevision
from app.modules.document_annotation.model import DocumentAnnotation
from app.modules.document_layout.model import (
    DocumentLayoutSection,
    DocumentSegmentationRevision,
)
from app.modules.document_reader.constants import (
    DEFAULT_ACTOR_SCOPE,
    RECORD_COUNTING_POLICY_VERSION,
)
from app.modules.document_reader.model import (
    PaperReaderState,
    ReaderBookmark,
    ReaderPreference,
    ReaderQuestion,
    ReaderSession,
)
from app.modules.document_reader.records import classify_annotation
from app.modules.document_reader.schema import CapabilityState, ReaderCapabilities
from app.modules.document_reader.service import ReaderSessionService
from app.modules.library_item.model import LibraryItem
from app.modules.medical_translation.provider import local_translation_artifact_ready
from app.modules.model_config.model import ModelConfig


class ReaderBootstrapProjector:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self._session = session
        self._actor_scope = actor_scope

    async def project(self, item_id: int) -> dict[str, object]:
        item = await self._session.get(LibraryItem, item_id)
        if item is None or item.document_id is None:
            from app.modules.document_reader.errors import ReaderResourceNotFoundError
            raise ReaderResourceNotFoundError("论文或 PDF 不存在")
        document = await self._session.get(Document, item.document_id)
        assert document is not None
        anchor = await self._session.scalar(select(DocumentAnchorRevision).where(DocumentAnchorRevision.document_id == document.id, DocumentAnchorRevision.state.in_(("ready", "review_required"))))
        segmentation = None if anchor is None else await self._session.scalar(select(DocumentSegmentationRevision).where(DocumentSegmentationRevision.anchor_revision_id == anchor.id, DocumentSegmentationRevision.state.in_(("ready", "review_required"))))
        latest = await self._session.scalar(
            select(ReaderSession)
            .where(
                ReaderSession.library_item_id == item.id,
                ReaderSession.actor_scope == self._actor_scope,
                ReaderSession.document_file_hash == document.file_hash,
            )
            .order_by(ReaderSession.last_seen_at.desc(), ReaderSession.id.desc())
        )
        preference = await self._session.scalar(select(ReaderPreference).where(ReaderPreference.actor_scope == self._actor_scope, ReaderPreference.document_id == document.id))
        favorite = await self._session.scalar(select(PaperReaderState).where(PaperReaderState.library_item_id == item.id, PaperReaderState.actor_scope == self._actor_scope))
        annotations = list((await self._session.scalars(select(DocumentAnnotation).where(DocumentAnnotation.document_id == document.id, DocumentAnnotation.deleted_at.is_(None)))).all())
        counts = {"highlights": 0, "annotations": 0}
        for annotation in annotations:
            counts[f"{classify_annotation(annotation.note)}s"] += 1
        counts["questions"] = int(await self._session.scalar(select(func.count()).select_from(ReaderQuestion).where(ReaderQuestion.document_id == document.id, ReaderQuestion.actor_scope == self._actor_scope, ReaderQuestion.deleted_at.is_(None))) or 0)
        counts["bookmarks"] = int(await self._session.scalar(select(func.count()).select_from(ReaderBookmark).where(ReaderBookmark.document_id == document.id, ReaderBookmark.actor_scope == self._actor_scope, ReaderBookmark.deleted_at.is_(None))) or 0)
        outline = []
        if segmentation is not None:
            sections = list((await self._session.scalars(
                select(DocumentLayoutSection)
                .where(DocumentLayoutSection.segmentation_revision_id == segmentation.id)
                .order_by(DocumentLayoutSection.first_page, DocumentLayoutSection.level, DocumentLayoutSection.id)
            )).all())
            outline = [
                {"id": section.id, "title": section.literal_title, "level": section.level,
                 "first_page": section.first_page, "last_page": section.last_page}
                for section in sections
            ]
        progress = await ReaderSessionService(self._session, self._actor_scope).progress(item.id)
        local_model_ready = local_translation_artifact_ready(
            settings.MEDICAL_TRANSLATION_LOCAL_MODEL_DIR,
            settings.MEDICAL_TRANSLATION_LOCAL_TOKENIZER_DIR,
        )
        configured_model = await self._session.scalar(
            select(ModelConfig.id).where(ModelConfig.is_default.is_(True))
        )
        translation_state = (
            CapabilityState.AVAILABLE
            if local_model_ready or configured_model is not None
            else CapabilityState.UNAVAILABLE
        )
        capabilities = ReaderCapabilities(outline=CapabilityState.AVAILABLE if outline else CapabilityState.NOT_READY, chapter_bundle=CapabilityState.AVAILABLE if segmentation else CapabilityState.NOT_READY, copilot=CapabilityState.AVAILABLE, translation=translation_state)
        return {
            "paper": {"paper_item_id": item.id, "document_id": document.id, "title": item.title, "journal": item.journal, "year": item.year, "paper_type": item.paper_type, "is_favorite": bool(favorite and favorite.is_favorite), "favorite_version": favorite.version if favorite else 1},
            "document": {"file_hash": document.file_hash, "page_count": document.parsed_page_count or 0, "content_url": f"/api/v1/documents/{document.id}/original"},
            "revision_fence": {"anchor_revision_id": anchor.id if anchor else None, "segmentation_revision_id": segmentation.id if segmentation else None},
            "resume": {"session_id": latest.id if latest else None, "page": latest.last_page if latest else 1, "viewport_offset_ratio": latest.viewport_offset_ratio if latest else 0},
            "progress": progress.model_dump(), "outline": outline, "record_counts": counts,
            "preference": {"view_mode": preference.view_mode if preference else "original", "zoom_percent": preference.zoom_percent if preference else 100, "left_panel_mode": preference.left_panel_mode if preference else "outline", "left_collapsed": preference.left_collapsed if preference else False, "right_panel_tab": preference.right_panel_tab if preference else "copilot", "focus_mode": preference.focus_mode if preference else False, "version": preference.version if preference else 1},
            "capabilities": capabilities.model_dump(mode="json"), "counting_policy_version": RECORD_COUNTING_POLICY_VERSION,
        }
