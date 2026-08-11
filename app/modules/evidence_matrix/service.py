"""Evidence-matrix orchestration: fields, documents, cells, versioning, export."""

import json
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.comparison.model import ComparisonTask
from app.modules.comparison.repository import ComparisonRepository
from app.modules.comparison.shared import (
    DEFAULT_FIELDS,
    FIELD_MAPPING,
    MISSING_VALUE,
    ComparisonField,
    SourceRef,
)
from app.modules.evidence_matrix.export import to_csv, to_markdown
from app.modules.evidence_matrix.model import (
    EvidenceMatrix,
    MatrixCell,
    MatrixDocument,
    MatrixField,
)
from app.modules.evidence_matrix.repository import EvidenceMatrixRepository
from app.modules.evidence_matrix.schema import (
    MAX_DOCUMENTS,
    MIN_DOCUMENTS,
    CellStatus,
    DocumentStatus,
    EvidenceMatrixRead,
    MatrixCellEdit,
    MatrixCellGenerated,
    MatrixCellRead,
    MatrixDocumentRead,
    MatrixDocumentUpdate,
    MatrixExportFormat,
    MatrixFieldRead,
    MatrixStatus,
    ReadingStatus,
    TopicRelevance,
)
from app.modules.library_item.repository import LibraryItemRepository
from app.modules.paper_analysis.repository import PaperAnalysisRepository
from app.modules.paper_analysis.schema import ClaimKind
from app.modules.research_context.service import ResearchContextService


class EvidenceMatrixService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = EvidenceMatrixRepository(session)
        self.comparisons = ComparisonRepository(session)
        self.analyses = PaperAnalysisRepository(session)
        self.library = LibraryItemRepository(session)
        self.research_contexts = ResearchContextService(session)

    # ---------------------------------------------------------------- CRUD
    async def create(
        self,
        name: str,
        description: str,
        fields: list[str] | None,
        source_comparison_id: int | None,
        research_context_id: int | None = None,
    ) -> EvidenceMatrixRead:
        if source_comparison_id is not None:
            source_task = await self.comparisons.get_task(source_comparison_id)
            if source_task is None:
                raise NotFoundError(f"Comparison not found: {source_comparison_id}")
            field_keys = self._comparison_fields(source_task)
            document_ids = json.loads(source_task.selected_document_ids)
        else:
            field_keys = fields if fields else [field.value for field in DEFAULT_FIELDS]
            document_ids = []
        if research_context_id is not None:
            await self.research_contexts.require(research_context_id)
        matrix = await self.repo.create(
            EvidenceMatrix(
                name=name,
                description=description,
                status="draft",
                version=1,
                source_comparison_id=source_comparison_id,
                research_context_id=research_context_id,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
        for position, field_key in enumerate(field_keys):
            await self.repo.add_field(
                MatrixField(
                    matrix_id=matrix.id,
                    field_key=field_key,
                    field_label=self._field_label(field_key),
                    position=position,
                    active=True,
                )
            )
        await self.repo.save()
        # 基于 comparison 创建时，继承已选文献（文献数可能超 10，不强制 3-10）。
        if document_ids:
            await self._add_documents(matrix.id, document_ids)
        return await self.get(matrix.id)

    async def get(self, matrix_id: int) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        fields = await self.repo.list_fields(matrix_id)
        documents = await self.repo.list_documents(matrix_id)
        cells = await self.repo.list_cells(matrix_id)
        return EvidenceMatrixRead(
            id=matrix.id,
            name=matrix.name,
            description=matrix.description,
            status=MatrixStatus(matrix.status),
            version=matrix.version,
            source_comparison_id=matrix.source_comparison_id,
            research_context_id=matrix.research_context_id,
            created_at=matrix.created_at,
            updated_at=matrix.updated_at,
            fields=[self._read_field(field) for field in fields],
            documents=[self._read_document(document) for document in documents],
            cells=[self._read_cell(cell) for cell in cells],
        )

    async def list_matrices(self, offset: int, limit: int) -> list[EvidenceMatrixRead]:
        # 方法名用 list_matrices 而非 list：避免遮蔽内置 list，破坏类内后续注解求值。
        return [
            await self.get(matrix.id)
            for matrix in await self.repo.list_matrices(offset, limit)
        ]

    async def count(self) -> int:
        return await self.repo.count_matrices()

    async def update(
        self,
        matrix_id: int,
        name: str | None,
        description: str | None,
        status: str | None,
        research_context_id: int | None = None,
    ) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        if name is not None:
            matrix.name = name
        if description is not None:
            matrix.description = description
        if status is not None:
            matrix.status = status
        if research_context_id is not None:
            await self.research_contexts.require(research_context_id)
            existing_documents = await self.repo.list_documents(matrix_id)
            await self.research_contexts.require_document_membership(
                research_context_id,
                [item.document_id for item in existing_documents],
            )
            matrix.research_context_id = research_context_id
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    async def delete(self, matrix_id: int) -> None:
        await self.repo.delete_matrix(await self._require_matrix(matrix_id))

    # ----------------------------------------------------------- documents
    async def add_documents(
        self, matrix_id: int, document_ids: list[int]
    ) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        existing = {
            document.document_id
            for document in await self.repo.list_documents(matrix_id)
        }
        current = len(existing)
        fresh = [
            document_id for document_id in document_ids if document_id not in existing
        ]
        if not fresh:
            return await self.get(matrix_id)
        # 边界校验：首次至少 3 篇，最终总数不超过 10（同 WP11 语义）。
        if current == 0 and len(fresh) < MIN_DOCUMENTS:
            raise ConflictError(
                f"Evidence matrix requires at least {MIN_DOCUMENTS} documents"
            )
        if current + len(fresh) > MAX_DOCUMENTS:
            raise ConflictError(
                f"Evidence matrix supports at most {MAX_DOCUMENTS} documents"
            )
        await self._add_documents(matrix_id, fresh)
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    async def remove_documents(
        self, matrix_id: int, document_ids: list[int]
    ) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        for document_id in document_ids:
            document = await self.repo.get_document(matrix_id, document_id)
            if document is not None:
                await self.repo.delete_document(document)
                await self.repo.delete_cells_for_document(matrix_id, document_id)
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    async def update_document(
        self, matrix_id: int, document_id: int, update: MatrixDocumentUpdate
    ) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        document = await self._require_document(matrix_id, document_id)
        if update.user_notes is not None:
            document.user_notes = update.user_notes
        if update.topic_relevance is not None:
            document.topic_relevance = update.topic_relevance.value
        if update.reading_status is not None:
            document.reading_status = update.reading_status.value
        if update.document_status is not None:
            document.document_status = update.document_status.value
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    # -------------------------------------------------------------- fields
    async def add_field(
        self, matrix_id: int, field_key: str, field_label: str
    ) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        existing = await self.repo.get_field(matrix_id, field_key)
        if existing is not None and existing.active:
            raise ConflictError(f"Field already exists: {field_key}")
        if existing is not None:
            # 复用已停用字段：重新激活并保留历史单元格数据。
            existing.active = True
            existing.field_label = field_label
            await self.repo.save()
        else:
            position = len(await self.repo.list_fields(matrix_id))
            await self.repo.add_field(
                MatrixField(
                    matrix_id=matrix_id,
                    field_key=field_key,
                    field_label=field_label,
                    position=position,
                    active=True,
                )
            )
        # 新增/复活的字段为已有文献补齐单元格，保证矩阵是完整矩形。
        await self._backfill_field_cells(matrix_id, field_key)
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    async def _backfill_field_cells(self, matrix_id: int, field_key: str) -> None:
        # 批量读取该矩阵全部单元格，内存判断存在性，避免每文档一次查询（N+1）。
        existing_cells = {
            (cell.document_id, cell.field_key)
            for cell in await self.repo.list_cells(matrix_id)
        }
        for document in await self.repo.list_documents(matrix_id):
            if (document.document_id, field_key) in existing_cells:
                continue
            generated = await self._evidence_value(document.document_id, field_key)
            await self.repo.add_cells(
                [
                    MatrixCell(
                        matrix_id=matrix_id,
                        document_id=document.document_id,
                        field_key=field_key,
                        cell_value=generated.cell_value,
                        sources=json.dumps(
                            [item.model_dump() for item in generated.sources]
                        ),
                        generated_value=generated.generated_value,
                        user_value=None,
                        status=generated.status.value,
                    )
                ]
            )

    async def remove_field(self, matrix_id: int, field_key: str) -> EvidenceMatrixRead:
        """停用字段而非物理删除：matrix_cells 保留历史值，供版本快照回溯。"""
        matrix = await self._require_matrix(matrix_id)
        field = await self._require_field(matrix_id, field_key)
        field.active = False
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    # --------------------------------------------------------------- cells
    async def edit_cell(
        self, matrix_id: int, edit: MatrixCellEdit
    ) -> EvidenceMatrixRead:
        matrix = await self._require_matrix(matrix_id)
        await self._require_document(matrix_id, edit.document_id)
        await self._require_field(matrix_id, edit.field_key)
        cell = await self.repo.get_cell(matrix_id, edit.document_id, edit.field_key)
        if cell is None:
            cell = MatrixCell(
                matrix_id=matrix_id,
                document_id=edit.document_id,
                field_key=edit.field_key,
                cell_value=edit.user_value,
                sources="[]",
                generated_value=None,
                user_value=edit.user_value,
                status=CellStatus.USER_EDITED.value,
            )
            await self.repo.add_cells([cell])
        else:
            cell.user_value = edit.user_value
            cell.cell_value = edit.user_value
            cell.status = CellStatus.USER_EDITED.value
            await self.repo.save()
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    # ------------------------------------------------------------ regenerate
    async def regenerate(self, matrix_id: int) -> EvidenceMatrixRead:
        """只更新 generated/missing 单元格；user_edited 单元格原样保留。"""
        matrix = await self._require_matrix(matrix_id)
        fields = [
            field for field in await self.repo.list_fields(matrix_id) if field.active
        ]
        documents = await self.repo.list_documents(matrix_id)
        for field in fields:
            for document in documents:
                cell = await self.repo.get_cell(
                    matrix_id, document.document_id, field.field_key
                )
                if cell is not None and cell.status == CellStatus.USER_EDITED.value:
                    continue
                generated = await self._evidence_value(
                    document.document_id, field.field_key
                )
                if cell is None:
                    cell = MatrixCell(
                        matrix_id=matrix_id,
                        document_id=document.document_id,
                        field_key=field.field_key,
                        cell_value=generated.cell_value,
                        sources=json.dumps(
                            [item.model_dump() for item in generated.sources]
                        ),
                        generated_value=generated.generated_value,
                        user_value=None,
                        status=generated.status.value,
                    )
                    await self.repo.add_cells([cell])
                else:
                    cell.cell_value = generated.cell_value
                    cell.generated_value = generated.generated_value
                    cell.sources = json.dumps(
                        [item.model_dump() for item in generated.sources]
                    )
                    cell.status = generated.status.value
                    await self.repo.save()
        matrix.version += 1
        matrix.updated_at = datetime.now(UTC)
        await self.repo.save()
        return await self.get(matrix_id)

    # -------------------------------------------------------------- export
    async def export(self, matrix_id: int, export_format: MatrixExportFormat) -> str:
        matrix = await self.get(matrix_id)
        if export_format == "csv":
            return to_csv(matrix)
        return to_markdown(matrix)

    # ------------------------------------------------------------ internals
    async def _add_documents(self, matrix_id: int, document_ids: list[int]) -> None:
        matrix = await self._require_matrix(matrix_id)
        if matrix.research_context_id is not None:
            await self.research_contexts.require_document_membership(
                matrix.research_context_id, document_ids
            )
        for document_id in document_ids:
            await self.repo.add_document(
                MatrixDocument(matrix_id=matrix_id, document_id=document_id)
            )
        for document_id in document_ids:
            for field_key in await self._active_field_keys(matrix_id):
                generated = await self._evidence_value(document_id, field_key)
                await self.repo.add_cells(
                    [
                        MatrixCell(
                            matrix_id=matrix_id,
                            document_id=document_id,
                            field_key=field_key,
                            cell_value=generated.cell_value,
                            sources=json.dumps(
                                [item.model_dump() for item in generated.sources]
                            ),
                            generated_value=generated.generated_value,
                            user_value=None,
                            status=generated.status.value,
                        )
                    ]
                )

    async def _active_field_keys(self, matrix_id: int) -> list[str]:
        fields = await self.repo.list_fields(matrix_id)
        return [field.field_key for field in fields if field.active]

    async def _evidence_value(
        self, document_id: int, field_key: str
    ) -> MatrixCellGenerated:
        """从 library_item + paper_analysis 聚合证据；缺失显式置 missing。

        与 WP11 同一语义：document_id 指向本地文档（documents.id），通过
        library_item.document_id 匹配正式收藏，从 PaperAnalysis 取带
        source_indices 的真实字段值。未知字段名（用户自定义字段）无证据，
        直接返回 missing；来源只绑定真实 PMID/DOI。
        """
        field = (
            ComparisonField(field_key)
            if field_key in {item.value for item in ComparisonField}
            else None
        )
        if field is None:
            return MatrixCellGenerated(document_id=document_id, field_key=field_key)
        library_items = await self.library.list_items(0, 1000, None)
        library_item = next(
            (item for item in library_items if item.document_id == document_id), None
        )
        if field == ComparisonField.SOURCE and library_item is not None:
            return MatrixCellGenerated(
                document_id=document_id,
                field_key=field_key,
                generated_value=library_item.title or MISSING_VALUE,
                sources=[
                    SourceRef(
                        pmid=library_item.pmid,
                        doi=library_item.doi,
                        locator="library_item",
                    )
                ],
            )
        analysis = await self.analyses.latest_for_document(document_id)
        if analysis is None or not analysis.structured_result or library_item is None:
            return MatrixCellGenerated(document_id=document_id, field_key=field_key)
        mapped_field = FIELD_MAPPING.get(field)
        if mapped_field is None:
            return MatrixCellGenerated(document_id=document_id, field_key=field_key)
        structured_result = json.loads(analysis.structured_result)
        analysis_field = structured_result.get(mapped_field, {})
        if analysis_field.get("kind") == ClaimKind.NOT_FOUND.value:
            return MatrixCellGenerated(document_id=document_id, field_key=field_key)
        sources = json.loads(analysis.sources or "[]")
        if not analysis_field.get("source_indices") or not sources:
            return MatrixCellGenerated(document_id=document_id, field_key=field_key)
        return MatrixCellGenerated(
            document_id=document_id,
            field_key=field_key,
            generated_value=analysis_field.get("value"),
            sources=[
                SourceRef(
                    pmid=library_item.pmid,
                    doi=library_item.doi,
                    locator=f"paper_analysis_source_{index}",
                )
                for index in analysis_field["source_indices"]
            ],
        )

    @staticmethod
    def _comparison_fields(task: ComparisonTask) -> list[str]:
        return json.loads(task.fields)

    @staticmethod
    def _field_label(field_key: str) -> str:
        try:
            field = ComparisonField(field_key)
        except ValueError:
            return field_key
        return {
            ComparisonField.STUDY_TYPE: "研究类型",
            ComparisonField.STUDY_POPULATION: "研究对象",
            ComparisonField.SAMPLE_SIZE: "样本量",
            ComparisonField.INTERVENTION: "干预或暴露",
            ComparisonField.COMPARATOR: "对照",
            ComparisonField.OUTCOME: "结局",
            ComparisonField.METHODS: "研究方法",
            ComparisonField.STATISTICS: "统计方法",
            ComparisonField.RESULTS: "主要结果",
            ComparisonField.NOVELTY: "创新点",
            ComparisonField.LIMITATIONS: "局限性",
            ComparisonField.SOURCE: "来源",
        }[field]

    async def _require_matrix(self, matrix_id: int) -> EvidenceMatrix:
        matrix = await self.repo.get_matrix(matrix_id)
        if matrix is None:
            raise NotFoundError(f"Evidence matrix not found: {matrix_id}")
        return matrix

    async def _require_document(
        self, matrix_id: int, document_id: int
    ) -> MatrixDocument:
        document = await self.repo.get_document(matrix_id, document_id)
        if document is None:
            raise NotFoundError(f"Document not in matrix: {document_id}")
        return document

    async def _require_field(self, matrix_id: int, field_key: str) -> MatrixField:
        field = await self.repo.get_field(matrix_id, field_key)
        if field is None or not field.active:
            raise NotFoundError(f"Field not found: {field_key}")
        return field

    def _read_document(self, document: MatrixDocument) -> MatrixDocumentRead:
        # DB 层存 str，读时收敛为 StrEnum（非法值由 StrEnum 抛错兜底，符合类型安全）。
        return MatrixDocumentRead(
            id=document.id,
            matrix_id=document.matrix_id,
            document_id=document.document_id,
            user_notes=document.user_notes,
            topic_relevance=TopicRelevance(document.topic_relevance),
            reading_status=ReadingStatus(document.reading_status),
            document_status=DocumentStatus(document.document_status),
            added_at=document.added_at,
        )

    def _read_field(self, field: MatrixField) -> MatrixFieldRead:
        return MatrixFieldRead(
            id=field.id,
            matrix_id=field.matrix_id,
            field_key=field.field_key,
            field_label=field.field_label,
            position=field.position,
            active=field.active,
        )

    def _read_cell(self, cell: MatrixCell) -> MatrixCellRead:
        return MatrixCellRead(
            id=cell.id,
            matrix_id=cell.matrix_id,
            document_id=cell.document_id,
            field_key=cell.field_key,
            cell_value=cell.cell_value or MISSING_VALUE,
            sources=[
                SourceRef.model_validate(item) for item in json.loads(cell.sources)
            ],
            generated_value=cell.generated_value,
            user_value=cell.user_value,
            status=CellStatus(cell.status),
        )
