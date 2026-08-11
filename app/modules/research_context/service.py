"""Business rules for grouping real research resources under one context."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.conversation.model import Conversation
from app.modules.document.repository import DocumentRepository
from app.modules.evidence_matrix.model import EvidenceMatrix
from app.modules.literature_search.model import LiteratureSearchTask
from app.modules.research_context.model import ResearchContext, ResearchContextDocument
from app.modules.research_context.repository import ResearchContextRepository
from app.modules.research_context.schema import (
    ResearchContextCreate,
    ResearchContextRead,
    ResearchContextUpdate,
)
from app.modules.writing_project.model import WritingProject


class ResearchContextService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ResearchContextRepository(session)
        self.documents = DocumentRepository(session)

    async def create(self, payload: ResearchContextCreate) -> ResearchContextRead:
        entity = await self.repository.create(ResearchContext(**payload.model_dump()))
        return await self._read(entity)

    async def list_contexts(self) -> list[ResearchContextRead]:
        return [await self._read(item) for item in await self.repository.list_contexts()]

    async def get(self, context_id: int) -> ResearchContextRead:
        return await self._read(await self.require(context_id))

    async def update(
        self, context_id: int, payload: ResearchContextUpdate
    ) -> ResearchContextRead:
        entity = await self.require(context_id)
        for field_name, value in payload.model_dump(exclude_none=True).items():
            setattr(entity, field_name, value)
        entity.updated_at = datetime.now(UTC)
        await self.repository.save()
        return await self._read(entity)

    async def add_documents(
        self, context_id: int, document_ids: list[int]
    ) -> ResearchContextRead:
        entity = await self.require(context_id)
        if len(set(document_ids)) != len(document_ids):
            raise ConflictError("Document IDs must be unique")
        for document_id in document_ids:
            if await self.documents.get(document_id) is None:
                raise NotFoundError(f"Document not found: {document_id}")
            if await self.repository.document_link(context_id, document_id) is None:
                await self.repository.add_document(
                    ResearchContextDocument(
                        research_context_id=context_id, document_id=document_id
                    )
                )
        entity.updated_at = datetime.now(UTC)
        await self.repository.save()
        return await self._read(entity)

    async def require(self, context_id: int) -> ResearchContext:
        entity = await self.repository.get(context_id)
        if entity is None:
            raise NotFoundError("Research context not found")
        return entity

    async def require_document_membership(
        self, context_id: int, document_ids: list[int]
    ) -> None:
        await self.require(context_id)
        for document_id in document_ids:
            if await self.repository.document_link(context_id, document_id) is None:
                raise ConflictError("Document is not linked to the research context")

    async def _read(self, entity: ResearchContext) -> ResearchContextRead:
        return ResearchContextRead(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            document_ids=[item.document_id for item in await self.repository.documents(entity.id)],
            conversation_ids=await self._resource_ids(Conversation, entity.id),
            evidence_matrix_ids=await self._resource_ids(EvidenceMatrix, entity.id),
            writing_project_ids=await self._resource_ids(WritingProject, entity.id),
            literature_search_task_ids=await self._resource_ids(
                LiteratureSearchTask, entity.id
            ),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    async def _resource_ids(self, model: type[Any], context_id: int) -> list[int]:
        # model 是 SQLAlchemy 模型类，列属性经 InstrumentedAttribute 处理，
        # 与静态类型不直接兼容；用 Any 保留运行时行为。
        result = await self.session.execute(
            select(model.id).where(model.research_context_id == context_id)
        )
        return list(result.scalars())
