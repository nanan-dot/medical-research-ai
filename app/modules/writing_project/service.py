"""写作项目业务编排：材料隔离、乐观并发与不可变快照。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.conversation.model import Citation
from app.modules.document.repository import DocumentRepository
from app.modules.evidence_matrix.model import MatrixCell
from app.modules.research_context.service import ResearchContextService
from app.modules.writing_project.model import (
    WritingEvidenceReference,
    WritingGeneratedContent,
    WritingProject,
    WritingUserMaterial,
    WritingVersion,
)
from app.modules.writing_project.repository import WritingProjectRepository
from app.modules.writing_project.schema import (
    GeneratedContent,
    UserMaterialCreate,
    UserMaterialRead,
    WritingEvidenceReferenceCreate,
    WritingEvidenceReferenceRead,
    WritingProjectCreate,
    WritingProjectRead,
    WritingProjectSnapshot,
    WritingProjectUpdate,
    WritingType,
    WritingVersionRead,
)
from app.modules.writing_project.versioning import restore_snapshot, snapshot_content


class WritingProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = WritingProjectRepository(session)
        self.documents = DocumentRepository(session)
        self.research_contexts = ResearchContextService(session)

    async def create(self, payload: WritingProjectCreate) -> WritingProjectRead:
        if payload.research_context_id is not None:
            await self.research_contexts.require(payload.research_context_id)
        entity = WritingProject(
            name=payload.name,
            writing_type=payload.writing_type,
            confidential=payload.confidential,
            research_context_id=payload.research_context_id,
            generated_content=WritingGeneratedContent(
                content_json=self._dump(payload.generated_content)
            ),
        )
        return self._read(await self.repository.create(entity))

    async def get(self, project_id: int) -> WritingProjectRead:
        return self._read(await self._require(project_id))

    async def list_projects(self) -> list[WritingProjectRead]:
        return [self._read(entity) for entity in await self.repository.list_projects()]

    async def update(
        self,
        project_id: int,
        payload: WritingProjectUpdate,
    ) -> WritingProjectRead:
        entity = await self._require(project_id)
        values: dict[str, object] = {
            "version": payload.expected_version + 1,
            "updated_at": datetime.now(UTC),
        }
        if payload.name is not None:
            values["name"] = payload.name
        if payload.confidential is not None:
            values["confidential"] = payload.confidential
        if payload.research_context_id is not None:
            await self.research_contexts.require(payload.research_context_id)
            await self.research_contexts.require_document_membership(
                payload.research_context_id,
                [
                    reference.document_id
                    for reference in entity.evidence_references
                    if reference.document_id is not None
                ],
            )
            values["research_context_id"] = payload.research_context_id
        if payload.generated_content is not None:
            entity.generated_content.content_json = self._dump(
                payload.generated_content
            )
        if not await self.repository.update_if_version(
            project_id, payload.expected_version, values
        ):
            raise ConflictError("Writing project version conflict; reload and retry")
        await self.session.refresh(entity)
        return self._read(entity)

    async def add_material(
        self,
        project_id: int,
        payload: UserMaterialCreate,
    ) -> UserMaterialRead:
        project = await self._require(project_id)
        material = await self.repository.add_material(
            WritingUserMaterial(project_id=project.id, **payload.model_dump())
        )
        await self.session.refresh(project, attribute_names=["materials"])
        return UserMaterialRead.model_validate(material)

    async def add_evidence_reference(
        self,
        project_id: int,
        payload: WritingEvidenceReferenceCreate,
    ) -> WritingEvidenceReferenceRead:
        project = await self._require(project_id)
        self._require_content_segment(project, payload.segment_id)
        reference = await self._resolve_reference(project, payload)
        stored = await self.repository.add_evidence_reference(reference)
        await self.session.refresh(project, attribute_names=["evidence_references"])
        return self._read_reference(stored)

    async def save_version(
        self, project_id: int, *, expected_version: int
    ) -> WritingVersionRead:
        entity = await self._require(project_id)
        self._check_version(entity, expected_version)
        prior_versions = await self.repository.list_versions(project_id)
        next_snapshot_version = (
            max((item.version for item in prior_versions), default=0) + 1
        )
        snapshot = snapshot_content(
            self._content(entity),
            version=next_snapshot_version,
            parent_version=prior_versions[-1].version if prior_versions else None,
        )
        stored = await self.repository.add_version(
            WritingVersion(
                project_id=project_id,
                version=snapshot.version,
                parent_version=snapshot.parent_version,
                content_json=self._dump(snapshot.content),
                evidence_references_json=self._dump_references(entity.evidence_references),
            )
        )
        return self._read_version(stored)

    async def list_versions(self, project_id: int) -> list[WritingVersionRead]:
        await self._require(project_id)
        return [
            self._read_version(item)
            for item in await self.repository.list_versions(project_id)
        ]

    async def restore_version(
        self,
        project_id: int,
        version: int,
        *,
        expected_version: int,
    ) -> WritingProjectRead:
        entity = await self._require(project_id)
        self._check_version(entity, expected_version)
        stored = await self.repository.get_version(project_id, version)
        if stored is None:
            raise NotFoundError("Writing project version not found")
        source = WritingProjectSnapshot(
            version=stored.version,
            parent_version=stored.parent_version,
            content=GeneratedContent.model_validate_json(stored.content_json),
        )
        restored = restore_snapshot(source, next_version=entity.version + 1)
        entity.generated_content.content_json = self._dump(restored.content)
        await self.repository.replace_evidence_references(
            entity,
            [
                self._reference_from_snapshot(project_id, item)
                for item in self._load_references(stored.evidence_references_json)
            ],
        )
        if not await self.repository.update_if_version(
            project_id,
            expected_version,
            {"version": restored.version, "updated_at": datetime.now(UTC)},
        ):
            raise ConflictError("Writing project version conflict; reload and retry")
        await self.repository.add_version(
            WritingVersion(
                project_id=project_id,
                version=restored.version,
                parent_version=restored.parent_version,
                content_json=self._dump(restored.content),
                evidence_references_json=self._dump_references(entity.evidence_references),
            )
        )
        await self.session.refresh(entity)
        return self._read(entity)

    async def delete(self, project_id: int) -> None:
        await self.repository.delete(await self._require(project_id))

    async def _require(self, project_id: int) -> WritingProject:
        entity = await self.repository.get(project_id)
        if entity is None:
            raise NotFoundError("Writing project not found")
        return entity

    @staticmethod
    def _check_version(entity: WritingProject, expected_version: int) -> None:
        if entity.version != expected_version:
            raise ConflictError("Writing project version conflict; reload and retry")

    @staticmethod
    def _dump(content: GeneratedContent) -> str:
        return json.dumps(content.model_dump(mode="json"), ensure_ascii=False)

    def _content(self, entity: WritingProject) -> GeneratedContent:
        content = GeneratedContent.model_validate_json(entity.generated_content.content_json)
        normalized_content = self._dump(content)
        if entity.generated_content.content_json != normalized_content:
            entity.generated_content.content_json = normalized_content
        return content

    def _require_content_segment(self, project: WritingProject, segment_id: str) -> None:
        if any(segment.id == segment_id for segment in self._content(project).segments):
            return
        raise ConflictError("Content segment not found in the writing project")

    async def _resolve_reference(
        self,
        project: WritingProject,
        payload: WritingEvidenceReferenceCreate,
    ) -> WritingEvidenceReference:
        if payload.source_type == "document":
            if payload.document_id is None:
                raise ConflictError("Document evidence requires document_id")
            document = await self.documents.get(payload.document_id)
            if document is None:
                raise NotFoundError(f"Document not found: {payload.document_id}")
            await self._require_context_document(project, document.id)
            return WritingEvidenceReference(
                project_id=project.id,
                segment_id=payload.segment_id,
                source_type=payload.source_type,
                document_id=document.id,
                page=None,
                section=None,
                evidence_text=None,
                citation_text=document.parsed_title,
                pmid=None,
                doi=None,
                locator=None,
            )
        if payload.source_type == "conversation_citation":
            if payload.conversation_citation_id is None:
                raise ConflictError("Conversation evidence requires conversation_citation_id")
            citation = await self.session.get(Citation, payload.conversation_citation_id)
            if citation is None:
                raise NotFoundError("Conversation citation not found")
            await self._require_context_document(project, citation.document_id)
            return WritingEvidenceReference(
                project_id=project.id,
                segment_id=payload.segment_id,
                source_type=payload.source_type,
                document_id=citation.document_id,
                conversation_citation_id=citation.id,
                page=citation.page,
                section=citation.section,
                evidence_text=citation.evidence_text,
                citation_text=citation.citation_text,
                pmid=None,
                doi=None,
                locator=None,
            )
        if payload.matrix_cell_id is None:
            raise ConflictError("Matrix evidence requires matrix_cell_id")
        cell = await self.session.get(MatrixCell, payload.matrix_cell_id)
        if cell is None:
            raise NotFoundError("Evidence matrix cell not found")
        await self._require_context_document(project, cell.document_id)
        sources = json.loads(cell.sources)
        source = sources[0] if len(sources) == 1 else {}
        return WritingEvidenceReference(
            project_id=project.id,
            segment_id=payload.segment_id,
            source_type=payload.source_type,
            document_id=cell.document_id,
            matrix_cell_id=cell.id,
            page=None,
            section=None,
            evidence_text=None,
            citation_text=None,
            pmid=source.get("pmid"),
            doi=source.get("doi"),
            locator=source.get("locator"),
        )

    async def _require_context_document(
        self, project: WritingProject, document_id: int
    ) -> None:
        if project.research_context_id is not None:
            await self.research_contexts.require_document_membership(
                project.research_context_id, [document_id]
            )

    @staticmethod
    def _dump_references(references: list[WritingEvidenceReference]) -> str:
        return json.dumps(
            [WritingProjectService._read_reference(item).model_dump() for item in references],
            ensure_ascii=False,
        )

    @staticmethod
    def _load_references(payload: str) -> list[WritingEvidenceReferenceRead]:
        return [
            WritingEvidenceReferenceRead.model_validate(item)
            for item in json.loads(payload or "[]")
        ]

    @staticmethod
    def _reference_from_snapshot(
        project_id: int, reference: WritingEvidenceReferenceRead
    ) -> WritingEvidenceReference:
        values = reference.model_dump(exclude={"id"})
        return WritingEvidenceReference(project_id=project_id, **values)

    def _read(self, entity: WritingProject) -> WritingProjectRead:
        return WritingProjectRead(
            id=entity.id,
            name=entity.name,
            writing_type=cast(WritingType, entity.writing_type),
            confidential=entity.confidential,
            research_context_id=entity.research_context_id,
            generated_content=self._content(entity),
            version=entity.version,
            user_materials=[
                UserMaterialRead.model_validate(item) for item in entity.materials
            ],
            evidence_references=[
                self._read_reference(item) for item in entity.evidence_references
            ],
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @classmethod
    def _read_version(cls, entity: WritingVersion) -> WritingVersionRead:
        return WritingVersionRead(
            version=entity.version,
            parent_version=entity.parent_version,
            content=GeneratedContent.model_validate_json(entity.content_json),
            created_at=entity.created_at,
            evidence_references=cls._load_references(entity.evidence_references_json),
        )

    @staticmethod
    def _read_reference(
        entity: WritingEvidenceReference,
    ) -> WritingEvidenceReferenceRead:
        return WritingEvidenceReferenceRead.model_validate(entity, from_attributes=True)
