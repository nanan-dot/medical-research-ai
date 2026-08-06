"""Orchestrate reusable analysis data into an evidence-bound comparison matrix."""

import csv
import io
import json
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import NotFoundError
from app.modules.comparison.model import ComparisonCell, ComparisonTask
from app.modules.comparison.repository import ComparisonRepository
from app.modules.comparison.schema import (
    COMPARISON_FIELDS,
    MISSING_VALUE,
    CellStatus,
    ComparisonCellEdit,
    ComparisonCellGenerated,
    ComparisonCellRead,
    ComparisonCreate,
    ComparisonField,
    ComparisonTaskRead,
    SourceRef,
)
from app.modules.library_item.repository import LibraryItemRepository
from app.modules.paper_analysis.repository import PaperAnalysisRepository
from app.modules.paper_analysis.schema import ClaimKind

ComparisonExportFormat = Literal["csv", "markdown"]

FIELD_MAPPING = {
    ComparisonField.STUDY_TYPE: "study_type",
    ComparisonField.STUDY_POPULATION: "population",
    ComparisonField.SAMPLE_SIZE: "sample_size",
    ComparisonField.INTERVENTION: "intervention_or_exposure",
    ComparisonField.COMPARATOR: "comparator",
    ComparisonField.OUTCOME: "primary_outcome",
    ComparisonField.METHODS: "research_question",
    ComparisonField.STATISTICS: "statistical_methods",
    ComparisonField.RESULTS: "main_results",
    ComparisonField.NOVELTY: "innovations",
    ComparisonField.LIMITATIONS: "limitations",
}


class ComparisonService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = ComparisonRepository(session)
        self.analyses = PaperAnalysisRepository(session)
        self.library = LibraryItemRepository(session)

    async def create(self, request: ComparisonCreate) -> ComparisonTaskRead:
        task = await self.repo.create_task(
            ComparisonTask(
                selected_document_ids=json.dumps(request.selected_document_ids),
                fields=json.dumps([field.value for field in COMPARISON_FIELDS]),
                status="completed",
                created_at=datetime.now(UTC),
            )
        )
        cells = [
            await self._generate_cell(task.id, document_id, field)
            for document_id in request.selected_document_ids
            for field in COMPARISON_FIELDS
        ]
        await self.repo.create_cells(cells)
        return await self.get(task.id)

    async def get(self, task_id: int) -> ComparisonTaskRead:
        task = await self._require_task(task_id)
        cells = await self.repo.cells_for_task(task.id)
        return ComparisonTaskRead(
            id=task.id,
            selected_document_ids=json.loads(task.selected_document_ids),
            fields=[ComparisonField(value) for value in json.loads(task.fields)],
            status=task.status,
            created_at=task.created_at,
            cells=[self._read_cell(cell) for cell in cells],
        )

    async def edit_cell(self, task_id: int, edit: ComparisonCellEdit) -> ComparisonTaskRead:
        cell = await self.repo.cell(task_id, edit.document_id, edit.field.value)
        if cell is None:
            raise NotFoundError("Comparison cell not found")
        cell.user_value = edit.user_value
        cell.cell_value = edit.user_value
        cell.status = CellStatus.USER_EDITED.value
        await self.repo.save()
        return await self.get(task_id)

    async def regenerate(self, task_id: int) -> ComparisonTaskRead:
        await self._require_task(task_id)
        for cell in await self.repo.cells_for_task(task_id):
            if cell.status == CellStatus.USER_EDITED.value:
                continue
            generated = await self._generate_cell(task_id, cell.document_id, ComparisonField(cell.field))
            cell.cell_value = generated.cell_value
            cell.generated_value = generated.generated_value
            cell.sources = generated.sources
            cell.status = generated.status
        await self.repo.save()
        return await self.get(task_id)

    async def export(self, task_id: int, export_format: ComparisonExportFormat) -> str:
        task = await self.get(task_id)
        if export_format == "csv":
            return self._to_csv(task)
        return self._to_markdown(task)

    async def _require_task(self, task_id: int) -> ComparisonTask:
        task = await self.repo.get_task(task_id)
        if task is None:
            raise NotFoundError(f"Comparison not found: {task_id}")
        return task

    async def _generate_cell(self, task_id: int, document_id: int, field: ComparisonField) -> ComparisonCell:
        generated = await self._evidence_value(document_id, field)
        return ComparisonCell(
            comparison_id=task_id,
            document_id=document_id,
            field=field.value,
            cell_value=generated.cell_value,
            generated_value=generated.generated_value,
            sources=json.dumps([item.model_dump() for item in generated.sources]),
            status=generated.status.value,
        )

    async def _evidence_value(self, document_id: int, field: ComparisonField) -> ComparisonCellGenerated:
        library_items = await self.library.list_items(0, 1000, None)
        library_item = next((item for item in library_items if item.document_id == document_id), None)
        if field == ComparisonField.SOURCE and library_item is not None:
            return ComparisonCellGenerated(
                document_id=document_id,
                field=field,
                generated_value=library_item.title or MISSING_VALUE,
                sources=[SourceRef(pmid=library_item.pmid, doi=library_item.doi, locator="library_item")],
            )
        analysis = await self.analyses.latest_for_document(document_id)
        if analysis is None or not analysis.structured_result or library_item is None:
            return ComparisonCellGenerated(document_id=document_id, field=field)
        mapped_field = FIELD_MAPPING.get(field)
        if mapped_field is None:
            return ComparisonCellGenerated(document_id=document_id, field=field)
        structured_result = json.loads(analysis.structured_result)
        analysis_field = structured_result.get(mapped_field, {})
        if analysis_field.get("kind") == ClaimKind.NOT_FOUND.value:
            return ComparisonCellGenerated(document_id=document_id, field=field)
        sources = json.loads(analysis.sources or "[]")
        if not analysis_field.get("source_indices") or not sources:
            return ComparisonCellGenerated(document_id=document_id, field=field)
        return ComparisonCellGenerated(
            document_id=document_id,
            field=field,
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

    def _read_cell(self, cell: ComparisonCell) -> ComparisonCellRead:
        return ComparisonCellRead(
            document_id=cell.document_id,
            field=ComparisonField(cell.field),
            cell_value=cell.cell_value or MISSING_VALUE,
            sources=[SourceRef.model_validate(item) for item in json.loads(cell.sources)],
            generated_value=cell.generated_value,
            user_value=cell.user_value,
            status=CellStatus(cell.status),
        )

    def _to_csv(self, task: ComparisonTaskRead) -> str:
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["field", *[f"document_{item}" for item in task.selected_document_ids]])
        for field in task.fields:
            row = [field.value]
            for document_id in task.selected_document_ids:
                cell = self._cell_for(task, field, document_id)
                row.append(cell.cell_value)
            writer.writerow(row)
        return output.getvalue()

    def _to_markdown(self, task: ComparisonTaskRead) -> str:
        header = ["字段", *[f"文档 {item}" for item in task.selected_document_ids]]
        lines = [f"# 多论文比较 #{task.id}", "", self._markdown_row(header), self._markdown_row(["---"] * len(header))]
        for field in task.fields:
            values = [field.value]
            values.extend(self._cell_for(task, field, document_id).cell_value for document_id in task.selected_document_ids)
            lines.append(self._markdown_row(values))
        return "\n".join(lines) + "\n"

    def _cell_for(self, task: ComparisonTaskRead, field: ComparisonField, document_id: int) -> ComparisonCellRead:
        return next(cell for cell in task.cells if cell.field == field and cell.document_id == document_id)

    def _markdown_row(self, values: list[str]) -> str:
        escaped_values = [value.replace("|", "\\|").replace("\n", "<br>") for value in values]
        return f"| {' | '.join(escaped_values)} |"
