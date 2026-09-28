"""研读交接的幂等写入。"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.document_anchor.model import (
    DocumentAnchorRevision,
    DocumentSourceAnchor,
)
from app.modules.document_reader.constants import DEFAULT_ACTOR_SCOPE
from app.modules.document_reader.errors import (
    ReaderResourceNotFoundError,
)
from app.modules.document_reader.idempotency import (
    ensure_payload_matches,
    payload_digest,
)
from app.modules.document_reader.model import (
    ReaderIdempotencyRecord,
    ResearchMaterialCandidate,
)
from app.modules.document_reader.schema import ResearchMaterialCreate
from app.modules.paper_library.model import PaperResearchRelation


class ReaderHandoffService:
    def __init__(self, session: AsyncSession, actor_scope: str = DEFAULT_ACTOR_SCOPE):
        self._session = session
        self._actor_scope = actor_scope

    async def candidate(self, document_id: int, payload: ResearchMaterialCreate, key: str) -> dict[str, object]:
        if not key:
            raise ValueError("Idempotency-Key is required")
        digest = payload_digest(payload.model_dump(mode="json"))
        existing = await self._session.scalar(select(ResearchMaterialCandidate).where(ResearchMaterialCandidate.actor_scope == self._actor_scope, ResearchMaterialCandidate.idempotency_key == key))
        if existing is not None:
            ensure_payload_matches(existing.idempotency_payload_hash, digest)
            return {"candidate_id": existing.id, "status": existing.status}
        anchor = await self._session.get(DocumentSourceAnchor, payload.source_anchor_id)
        revision = (
            None
            if anchor is None
            else await self._session.get(DocumentAnchorRevision, anchor.anchor_revision_id)
        )
        if anchor is None or revision is None or revision.document_id != document_id:
            raise ReaderResourceNotFoundError("SourceAnchor 不属于该文档")
        entity = ResearchMaterialCandidate(actor_scope=self._actor_scope, research_context_id=payload.research_context_id, document_id=document_id, source_anchor_id=payload.source_anchor_id, candidate_type=payload.candidate_type, title=payload.title, note=payload.note, status="candidate", idempotency_key=key, idempotency_payload_hash=digest)
        try:
            async with self._session.begin_nested():
                self._session.add(entity)
                await self._session.flush()
        except IntegrityError:
            existing = await self._session.scalar(select(ResearchMaterialCandidate).where(ResearchMaterialCandidate.actor_scope == self._actor_scope, ResearchMaterialCandidate.idempotency_key == key))
            if existing is None:
                raise
            ensure_payload_matches(existing.idempotency_payload_hash, digest)
            return {"candidate_id": existing.id, "status": existing.status}
        return {"candidate_id": entity.id, "status": entity.status}

    async def workspace(self, item_id: int, research_context_id: int, key: str) -> dict[str, object]:
        if not key:
            raise ValueError("Idempotency-Key is required")
        digest = payload_digest({"item_id": item_id, "research_context_id": research_context_id})
        idempotency = await self._session.scalar(select(ReaderIdempotencyRecord).where(ReaderIdempotencyRecord.actor_scope == self._actor_scope, ReaderIdempotencyRecord.action == "study_workspace", ReaderIdempotencyRecord.idempotency_key == key))
        if idempotency is not None:
            ensure_payload_matches(idempotency.payload_hash, digest)
            return {"workspace_id": idempotency.resource_id, "destination": f"/papers/{item_id}/deep-reading?research_context_id={research_context_id}"}
        relation = await self._session.scalar(select(PaperResearchRelation).where(PaperResearchRelation.library_item_id == item_id, PaperResearchRelation.research_context_id == research_context_id))
        if relation is None:
            relation = PaperResearchRelation(library_item_id=item_id, research_context_id=research_context_id, role="reading", version=1)
            try:
                async with self._session.begin_nested():
                    self._session.add(relation)
                    await self._session.flush()
            except IntegrityError:
                relation = await self._session.scalar(select(PaperResearchRelation).where(PaperResearchRelation.library_item_id == item_id, PaperResearchRelation.research_context_id == research_context_id))
                if relation is None:
                    raise
        idempotency_record = ReaderIdempotencyRecord(actor_scope=self._actor_scope, action="study_workspace", idempotency_key=key, payload_hash=digest, resource_id=relation.id)
        try:
            async with self._session.begin_nested():
                self._session.add(idempotency_record)
                await self._session.flush()
        except IntegrityError:
            existing = await self._session.scalar(select(ReaderIdempotencyRecord).where(ReaderIdempotencyRecord.actor_scope == self._actor_scope, ReaderIdempotencyRecord.action == "study_workspace", ReaderIdempotencyRecord.idempotency_key == key))
            if existing is None:
                raise
            ensure_payload_matches(existing.payload_hash, digest)
            return {"workspace_id": existing.resource_id, "destination": f"/papers/{item_id}/deep-reading?research_context_id={research_context_id}"}
        return {"workspace_id": relation.id, "destination": f"/papers/{item_id}/deep-reading?research_context_id={research_context_id}"}
