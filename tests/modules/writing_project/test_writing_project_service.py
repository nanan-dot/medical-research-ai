from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.database import Base
from app.modules.writing_project.model import WritingUserMaterial
from app.modules.writing_project.schema import (
    GeneratedContent,
    UserMaterialCreate,
    WritingProjectCreate,
    WritingProjectUpdate,
)
from app.modules.writing_project.service import WritingProjectService


@pytest.fixture
async def service(tmp_path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{(tmp_path / 'writing.db').as_posix()}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield WritingProjectService(session)
    await engine.dispose()


@pytest.mark.asyncio
async def test_crud_preserves_user_material_during_generated_edit(service: WritingProjectService) -> None:
    project = await service.create(WritingProjectCreate(name="Review", writing_type="review"))
    material = await service.add_material(
        project.id,
        UserMaterialCreate(text="private note", source_document_id=42),
    )
    edited = await service.update(
        project.id,
        WritingProjectUpdate(
            generated_content=GeneratedContent(sections=[{"id": "s1", "title": "背景"}]),
            expected_version=1,
        ),
    )
    assert edited.version == 2
    assert edited.user_materials == [material]
    assert edited.user_materials[0].text == "private note"


@pytest.mark.asyncio
async def test_snapshot_is_immutable_and_restore_creates_new_version(
    service: WritingProjectService,
) -> None:
    project = await service.create(WritingProjectCreate(name="Review", writing_type="review"))
    first = await service.save_version(project.id, expected_version=1)
    await service.update(
        project.id,
        WritingProjectUpdate(
            generated_content=GeneratedContent(sections=[{"id": "s1", "title": "Changed"}]),
            expected_version=1,
        ),
    )
    restored = await service.restore_version(project.id, first.version, expected_version=2)
    versions = await service.list_versions(project.id)
    assert restored.version == 3
    assert restored.generated_content == first.content
    assert versions[0].content.sections == []


@pytest.mark.asyncio
async def test_repeated_save_creates_distinct_snapshot_versions(
    service: WritingProjectService,
) -> None:
    project = await service.create(WritingProjectCreate(name="Review", writing_type="review"))
    first = await service.save_version(project.id, expected_version=1)
    second = await service.save_version(project.id, expected_version=1)
    assert (first.version, second.version) == (1, 2)


@pytest.mark.asyncio
async def test_concurrent_update_is_rejected(service: WritingProjectService) -> None:
    project = await service.create(WritingProjectCreate(name="Review", writing_type="review"))
    await service.update(project.id, WritingProjectUpdate(name="A", expected_version=1))
    with pytest.raises(Exception, match="version"):
        await service.update(project.id, WritingProjectUpdate(name="B", expected_version=1))


def test_material_source_reference_has_no_delete_cascade_to_library_asset() -> None:
    column = WritingUserMaterial.__table__.c.source_document_id
    assert not column.foreign_keys
