"""论文阅读工作区 API。"""

import hashlib
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.modules.document_reader.assets import ReaderAssetService
from app.modules.document_reader.bootstrap import ReaderBootstrapProjector
from app.modules.document_reader.chapter import ChapterBundleProjector
from app.modules.document_reader.constants import (
    HISTORY_MAX_LIMIT,
    TRANSLATION_CONTRACT_VERSION,
)
from app.modules.document_reader.handoff import ReaderHandoffService
from app.modules.document_reader.history import ReaderHistoryService
from app.modules.document_reader.record_projector import ReaderRecordProjector
from app.modules.document_reader.schema import (
    BookmarkCreate,
    CapabilityState,
    ExposureBatchCreate,
    PreferenceUpdate,
    ProgressRead,
    QuestionCreate,
    QuestionStatus,
    ReaderPositionUpdate,
    ResearchMaterialCreate,
    SessionCreate,
    SessionRead,
    TranslationCapabilityRead,
)
from app.modules.document_reader.service import ReaderSessionService
from app.modules.library_item.model import LibraryItem
from app.modules.medical_translation.provider import local_translation_artifact_ready
from app.modules.model_config.model import ModelConfig

router = APIRouter(prefix="/paper-reader", tags=["paper-reader"])


@router.get("/items/{paper_item_id}/bootstrap")
async def bootstrap(paper_item_id: int, response: Response, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    result = await ReaderBootstrapProjector(session).project(paper_item_id)
    serialized = json.dumps(result, default=str, ensure_ascii=False, sort_keys=True)
    response.headers["ETag"] = f'W/"{hashlib.sha256(serialized.encode()).hexdigest()}"'
    return result


@router.post("/items/{paper_item_id}/sessions", response_model=SessionRead)
async def create_session(paper_item_id: int, payload: SessionCreate, session: Annotated[AsyncSession, Depends(get_session)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", max_length=128)] = "") -> SessionRead:
    return await ReaderSessionService(session).create_or_reuse(paper_item_id, payload, idempotency_key)


@router.patch("/sessions/{session_id}/position", response_model=SessionRead)
async def update_position(session_id: int, payload: ReaderPositionUpdate, session: Annotated[AsyncSession, Depends(get_session)]) -> SessionRead:
    return await ReaderSessionService(session).update_position(session_id, payload)


@router.post("/sessions/{session_id}/exposures:batch", response_model=ProgressRead)
async def add_exposures(session_id: int, payload: ExposureBatchCreate, session: Annotated[AsyncSession, Depends(get_session)]) -> ProgressRead:
    return await ReaderSessionService(session).add_exposures(session_id, payload)


@router.post("/sessions/{session_id}/close", response_model=SessionRead)
async def close_session(session_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> SessionRead:
    return await ReaderSessionService(session).close(session_id)


@router.get("/items/{paper_item_id}/progress", response_model=ProgressRead)
async def progress(paper_item_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> ProgressRead:
    return await ReaderSessionService(session).progress(paper_item_id)


@router.get("/history")
async def history(session: Annotated[AsyncSession, Depends(get_session)], query: str | None = None, cursor: str | None = None, limit: int = Query(20, ge=1, le=HISTORY_MAX_LIMIT)) -> dict[str, object]:
    return await ReaderHistoryService(session).list(query, cursor, limit)


@router.delete("/history/{session_id}", status_code=204)
async def hide_history(session_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> Response:
    await ReaderHistoryService(session).hide(session_id)
    return Response(status_code=204)


@router.delete("/history", status_code=204)
async def clear_history(session: Annotated[AsyncSession, Depends(get_session)]) -> Response:
    await ReaderHistoryService(session).clear()
    return Response(status_code=204)


@router.post("/documents/{document_id}/research-material-candidates")
async def add_candidate(document_id: int, payload: ResearchMaterialCreate, session: Annotated[AsyncSession, Depends(get_session)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", max_length=128)] = "") -> dict[str, object]:
    return await ReaderHandoffService(session).candidate(document_id, payload, idempotency_key)


@router.post("/items/{paper_item_id}/study-workspace")
async def study_workspace(paper_item_id: int, research_context_id: int, session: Annotated[AsyncSession, Depends(get_session)], idempotency_key: Annotated[str, Header(alias="Idempotency-Key", max_length=128)] = "") -> dict[str, object]:
    return await ReaderHandoffService(session).workspace(paper_item_id, research_context_id, idempotency_key)


@router.get("/capabilities/translation", response_model=TranslationCapabilityRead)
async def translation_capability(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TranslationCapabilityRead:
    local_model_ready = local_translation_artifact_ready(
        settings.MEDICAL_TRANSLATION_LOCAL_MODEL_DIR,
        settings.MEDICAL_TRANSLATION_LOCAL_TOKENIZER_DIR,
    )
    configured_model = await session.scalar(
        select(ModelConfig.id).where(ModelConfig.is_default.is_(True))
    )
    state = CapabilityState.AVAILABLE if local_model_ready or configured_model else CapabilityState.UNAVAILABLE
    return TranslationCapabilityRead(
        state=state,
        contract_version=TRANSLATION_CONTRACT_VERSION,
        endpoint="/api/v1/documents/{document_id}/translation-jobs" if state == CapabilityState.AVAILABLE else None,
    )


@router.put("/items/{paper_item_id}/favorite")
async def set_favorite(paper_item_id: int, is_favorite: bool, expected_version: int, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    return await ReaderAssetService(session).favorite(paper_item_id, is_favorite, expected_version)


@router.patch("/items/{paper_item_id}/preferences")
async def update_preference(paper_item_id: int, document_id: int, payload: PreferenceUpdate, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    item = await session.get(LibraryItem, paper_item_id)
    if item is None or item.document_id != document_id:
        from app.modules.document_reader.errors import ReaderResourceNotFoundError
        raise ReaderResourceNotFoundError("论文与文档不匹配")
    return await ReaderAssetService(session).preference(document_id, payload)


@router.post("/documents/{document_id}/bookmarks")
async def create_bookmark(document_id: int, payload: BookmarkCreate, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    return await ReaderAssetService(session).bookmark(document_id, payload)


@router.delete("/documents/{document_id}/bookmarks/{bookmark_id}", status_code=204)
async def delete_bookmark(document_id: int, bookmark_id: int, expected_version: int, session: Annotated[AsyncSession, Depends(get_session)]) -> Response:
    await ReaderAssetService(session).delete_bookmark(document_id, bookmark_id, expected_version)
    return Response(status_code=204)


@router.post("/documents/{document_id}/questions")
async def create_question(document_id: int, payload: QuestionCreate, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    return await ReaderAssetService(session).question(document_id, payload)


@router.patch("/documents/{document_id}/questions/{question_id}")
async def update_question(document_id: int, question_id: int, question_status: QuestionStatus, expected_version: int, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    return await ReaderAssetService(session).update_question(document_id, question_id, question_status, expected_version)


@router.delete("/documents/{document_id}/questions/{question_id}", status_code=204)
async def delete_question(document_id: int, question_id: int, expected_version: int, session: Annotated[AsyncSession, Depends(get_session)]) -> Response:
    await ReaderAssetService(session).delete_question(document_id, question_id, expected_version)
    return Response(status_code=204)


@router.get("/documents/{document_id}/records/summary")
async def record_summary(document_id: int, session: Annotated[AsyncSession, Depends(get_session)], record_type: str | None = None, section_id: int | None = None, query: str | None = None) -> dict[str, object]:
    return await ReaderRecordProjector(session).summary(document_id, record_type=record_type, section_id=section_id, query=query)


@router.get("/documents/{document_id}/records")
async def records(document_id: int, session: Annotated[AsyncSession, Depends(get_session)], record_type: str | None = None, section_id: int | None = None, query: str | None = None, cursor: str | None = None, limit: int = Query(50, ge=1, le=100)) -> dict[str, object]:
    return await ReaderRecordProjector(session).list_records(document_id, record_type=record_type, section_id=section_id, query=query, cursor=cursor, limit=limit)


@router.get("/documents/{document_id}/chapter-bundle")
async def chapter_bundle(document_id: int, section_id: int, expected_anchor_revision_id: int, expected_segmentation_revision_id: int, session: Annotated[AsyncSession, Depends(get_session)]) -> dict[str, object]:
    return await ChapterBundleProjector(session).project(document_id, section_id, expected_anchor_revision_id, expected_segmentation_revision_id)
