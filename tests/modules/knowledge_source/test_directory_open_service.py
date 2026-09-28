"""安全目录打开的行为测试；从不真的启动系统资源管理器。"""

from pathlib import Path

import pytest

pytest_plugins = ["tests.modules.knowledge_source.test_service"]

from app.common.exceptions import FeatureUnavailableError
from app.core.config import Settings
from app.modules.knowledge_source.directory_open_service import (
    DirectoryOpenAdapter,
    KnowledgeSourceDirectoryOpenService,
)
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.schema import (
    KnowledgeSourceCreate,
    KnowledgeSourceType,
)
from app.modules.knowledge_source.service import KnowledgeSourceService


class RecordingDirectoryOpenAdapter(DirectoryOpenAdapter):
    """测试替身：记录输入而不产生操作系统副作用。"""

    def __init__(self) -> None:
        self.opened: Path | None = None

    def open(self, directory: Path) -> None:
        self.opened = directory


@pytest.mark.asyncio
async def test_open_directory_requires_explicit_local_desktop_mode(session, tmp_path: Path) -> None:
    """AC-OPEN-02：默认关闭时不得调用适配器。"""
    root = tmp_path / "source"
    root.mkdir()
    source = await KnowledgeSourceService(session).create(
        KnowledgeSourceCreate(name="source", source_type=KnowledgeSourceType.LOCAL_FOLDER, root_path=str(root))
    )
    adapter = RecordingDirectoryOpenAdapter()
    service = KnowledgeSourceDirectoryOpenService(
        KnowledgeSourceRepository(session), Settings(), adapter
    )
    with pytest.raises(FeatureUnavailableError):
        await service.open_source_directory(source.id)
    assert adapter.opened is None


@pytest.mark.asyncio
async def test_open_directory_uses_only_registered_source_path(session, tmp_path: Path) -> None:
    """AC-OPEN-01/04：调用方只有 source_id，适配器接到经过重验的目录。"""
    root = tmp_path / "source"
    root.mkdir()
    source = await KnowledgeSourceService(session).create(
        KnowledgeSourceCreate(name="source", source_type=KnowledgeSourceType.LOCAL_FOLDER, root_path=str(root))
    )
    adapter = RecordingDirectoryOpenAdapter()
    settings = Settings(ENABLE_LOCAL_DIRECTORY_OPEN=True, LOCAL_DESKTOP_MODE=True)
    await KnowledgeSourceDirectoryOpenService(
        KnowledgeSourceRepository(session), settings, adapter
    ).open_source_directory(source.id)
    assert adapter.opened == root.resolve()
