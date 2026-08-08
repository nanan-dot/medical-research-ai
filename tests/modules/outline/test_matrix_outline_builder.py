import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.common.exceptions import ConflictError
from app.modules.evidence_matrix.model import MatrixCell
from app.modules.outline.model import Outline
from app.modules.outline.outline_builder import build_outline
from app.modules.outline.schema import OutlineCreate, OutlineSection, OutlineUpdate
from app.modules.outline.service import OutlineService


def _cell(text: str = "Observed result", sources: str | None = None) -> MatrixCell:
    return MatrixCell(
        matrix_id=1,
        document_id=1,
        field_key="results",
        cell_value=text,
        sources=sources or json.dumps([{"pmid": "12345", "locator": "abstract"}]),
        status="generated",
    )


def test_review_has_seven_sections_and_traceable_matrix_claim() -> None:
    sections = build_outline("review", [_cell()], [])
    assert [section.title for section in sections] == [
        "背景", "主题分类", "主要机制", "研究证据", "争议", "局限", "未来方向"
    ]
    claim = sections[3].claims[0]
    assert claim.evidence[0].pmid == "12345"
    assert not claim.missing_evidence


def test_proposal_marks_direction_as_unconfirmed_candidate() -> None:
    sections = build_outline("proposal", [_cell()], ["Question"])
    candidate = sections[3].claims[0]
    assert candidate.status == "candidate"
    assert "拟研究" in candidate.text
    assert candidate.missing_evidence


def test_forbidden_factual_wording_is_rejected() -> None:
    with pytest.raises(ValueError, match="prohibited"):
        build_outline("review", [_cell("该方案必然有效")], [])


class _OutlineRepo:
    def __init__(self) -> None:
        self.entity: Outline | None = None

    async def get(self, _id: int) -> Outline | None:
        return self.entity

    async def create(self, entity: Outline) -> Outline:
        entity.id = 1
        entity.version = 1
        entity.confirmed_by_user = False
        entity.confirmed_at = None
        entity.created_at = datetime.now(UTC)
        self.entity = entity
        return entity

    async def save(self, entity: Outline) -> Outline:
        self.entity = entity
        return entity


class _MatrixRepo:
    def __init__(self) -> None:
        self.matrix = SimpleNamespace(version=2, updated_at=datetime(2026, 8, 8, tzinfo=UTC))

    async def get_matrix(self, _id: int):
        return self.matrix

    async def list_cells(self, _id: int):
        return [_cell()]

    async def list_documents(self, _id: int):
        return [object(), object()]


class _DirectionRepo:
    async def list_for_matrix(self, _id: int):
        return [SimpleNamespace(name="Question")]


def _service() -> OutlineService:
    service = object.__new__(OutlineService)
    service.r = _OutlineRepo()
    service.m = _MatrixRepo()
    service.d = _DirectionRepo()
    return service


@pytest.mark.asyncio
async def test_create_records_matrix_snapshot_metadata() -> None:
    result = await _service().create(OutlineCreate(matrix_id=1, kind="proposal"))
    assert result.based_on_matrix_version == 2
    assert result.document_count == 2
    assert len(result.sections) == 7


@pytest.mark.asyncio
async def test_edit_increments_version_and_revokes_confirmation() -> None:
    service = _service()
    created = await service.create(OutlineCreate(matrix_id=1, kind="review"))
    await service.confirm(created.id)
    update = OutlineUpdate(sections=[OutlineSection(title="背景", claims=[])])
    edited = await service.update(created.id, update)
    assert edited.version == 2
    assert not edited.confirmed_by_user
    assert edited.confirmed_at is None


@pytest.mark.asyncio
async def test_edit_rejects_stale_matrix_snapshot() -> None:
    service = _service()
    created = await service.create(OutlineCreate(matrix_id=1, kind="review"))
    service.m.matrix.version = 3
    with pytest.raises(ConflictError, match="version changed"):
        await service.update(
            created.id,
            OutlineUpdate(sections=[OutlineSection(title="背景", claims=[])]),
        )
