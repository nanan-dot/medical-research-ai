"""R2-WP12 evidence matrix service tests (offline, no LLM / network).

Covers: CRUD, document add/remove with 3-10 boundary, field add/remove
without data loss, user notes isolation, versioning on regenerate,
CSV escaping, and user-edited cells surviving regeneration.
"""


import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError, NotFoundError
from app.core import models  # noqa: F401  # 注册全部 ORM 表，外键才能解析
from app.core.database import Base
from app.modules.evidence_matrix.model import (
    EvidenceMatrix,
)
from app.modules.evidence_matrix.schema import (
    CellStatus,
    MatrixCellEdit,
    MatrixCreate,
    MatrixDocumentUpdate,
    ReadingStatus,
)
from app.modules.evidence_matrix.service import EvidenceMatrixService


@pytest.fixture
async def service(tmp_path):
    """内存级服务实例：独立 SQLite 引擎 + 建表，避免污染开发库。"""
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'matrix.db').as_posix()}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as session:
        yield EvidenceMatrixService(session)
    await engine.dispose()


async def _create_matrix(svc, name: str = "EGFR 综述矩阵") -> EvidenceMatrix:
    request = MatrixCreate(name=name, description="测试矩阵")
    result = await svc.create(
        name=request.name,
        description=request.description,
        fields=request.fields,
        source_comparison_id=request.source_comparison_id,
    )
    return result.model_dump()


async def _seed_documents(svc, matrix_id: int, count: int = 3) -> None:
    await svc.add_documents(matrix_id, list(range(1, count + 1)))


async def test_create_matrix_sets_default_fields(service):
    """创建矩阵后默认比较字段存在，且不含手工字段。"""
    data = await _create_matrix(service)
    assert data["name"] == "EGFR 综述矩阵"
    assert len(data["fields"]) >= 10  # 默认比较字段集
    assert data["documents"] == []


async def test_document_boundary_3_to_10(service):
    """3 篇可加、10 篇可加；低于 3 或高于 10 拒绝。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    # 2 篇 → 拒绝（少于 3）
    with pytest.raises(ConflictError, match="3"):
        await service.add_documents(matrix_id, [1, 2])
    # 3 篇 → 成功
    await _seed_documents(service, matrix_id, 3)
    # 11 篇（3+8）→ 拒绝（超过 10）
    with pytest.raises(ConflictError, match="10"):
        await service.add_documents(matrix_id, list(range(4, 12)))


async def test_add_field_backfills_cells(service):
    """新增字段后，已有文档自动补齐该字段的单元格（缺失态）。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    await service.add_field(matrix_id, "funding", "资助来源")
    refreshed = await service.get(matrix_id)
    field_keys = [f.field_key for f in refreshed.fields]
    assert "funding" in field_keys
    funding_cells = [c for c in refreshed.cells if c.field_key == "funding"]
    assert len(funding_cells) == 3
    assert all(c.status == CellStatus.MISSING for c in funding_cells)


async def test_remove_field_keeps_other_cells(service):
    """删除字段是软删除（active=False）：字段从列表消失，但单元格保留供版本回溯。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    # 编辑一个单元格，再删除该字段
    await service.edit_cell(matrix_id, MatrixCellEdit(document_id=1, field_key="study_type", user_value="队列研究"))
    await service.remove_field(matrix_id, "study_type")
    after = await service.get(matrix_id)
    assert all(f.field_key != "study_type" for f in after.fields)  # 字段列表移除
    study_cells = [c for c in after.cells if c.field_key == "study_type"]
    assert len(study_cells) == 3  # 单元格保留（软删除，不丢数据）
    remaining = [c for c in after.cells if c.document_id == 1 and c.field_key != "study_type"]
    assert remaining  # 其他字段单元格仍在


async def test_user_notes_isolated_from_generated(service):
    """用户备注独立存储，不进入 cell_value。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    await service.update_document(
        matrix_id,
        1,
        MatrixDocumentUpdate(user_notes="这篇是核心证据", reading_status=ReadingStatus.READING),
    )
    refreshed = await service.get(matrix_id)
    doc = next(d for d in refreshed.documents if d.document_id == 1)
    assert doc.user_notes == "这篇是核心证据"
    assert doc.reading_status == ReadingStatus.READING


async def test_regenerate_preserves_user_edited_cells(service):
    """重新生成：user_edited 单元格保留，generated/missing 更新。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    await service.edit_cell(matrix_id, MatrixCellEdit(document_id=1, field_key="study_type", user_value="人工填写的类型"))
    before = await service.get(matrix_id)
    version_before = before.version
    await service.regenerate(matrix_id)
    after = await service.get(matrix_id)
    assert after.version > version_before  # 版本递增
    edited = next(c for c in after.cells if c.document_id == 1 and c.field_key == "study_type")
    assert edited.cell_value == "人工填写的类型"
    assert edited.status == CellStatus.USER_EDITED


async def test_export_csv_escapes_commas_and_quotes(service):
    """CSV 导出正确处理逗号/引号转义。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    await service.edit_cell(
        matrix_id,
        MatrixCellEdit(document_id=1, field_key="study_type", user_value='含"引号,和逗号'),
    )
    csv_text = await service.export(matrix_id, "csv")
    assert '"含""引号,和逗号"' in csv_text  # 引号转义为双引号


async def test_export_markdown_has_headers(service):
    """Markdown 导出含表头与矩阵名。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    md = await service.export(matrix_id, "markdown")
    assert "EGFR 综述矩阵" in md
    assert "|" in md  # Markdown 表格行


async def test_delete_matrix_removes_all_rows(service):
    """删除矩阵级联移除文档/字段/单元格。"""
    data = await _create_matrix(service)
    matrix_id = data["id"]
    await _seed_documents(service, matrix_id, 3)
    await service.delete(matrix_id)
    with pytest.raises(NotFoundError):
        await service.get(matrix_id)
