"""知识来源目录的受限本机打开能力。"""

import os
import subprocess
import sys
from pathlib import Path

from app.common.exceptions import (
    FeatureUnavailableError,
    InvalidPathError,
    NotFoundError,
    PermissionDeniedError,
    TemporarilyUnavailableError,
)
from app.core.config import Settings
from app.modules.knowledge_source.model import KnowledgeSource
from app.modules.knowledge_source.repository import KnowledgeSourceRepository
from app.modules.knowledge_source.service import normalize_authorized_directory


class DirectoryOpenAdapter:
    """隔离平台调用，便于安全测试替换且不接受 shell 字符串。"""

    def open(self, directory: Path) -> None:
        if sys.platform != "win32":
            raise FeatureUnavailableError("Local directory opening is unsupported")
        try:
            subprocess.Popen(["explorer.exe", str(directory)], shell=False)
        except OSError as exc:
            raise TemporarilyUnavailableError("Unable to open local directory") from exc


class KnowledgeSourceDirectoryOpenService:
    """仅按来源 ID 重取并验证已授权目录后，才允许本机打开。"""

    def __init__(
        self,
        repository: KnowledgeSourceRepository,
        settings: Settings,
        adapter: DirectoryOpenAdapter | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._adapter = adapter or DirectoryOpenAdapter()

    async def open_source_directory(self, source_id: int) -> None:
        self._require_local_desktop_feature()
        source = await self._repository.get(source_id)
        if source is None:
            raise NotFoundError(f"KnowledgeSource not found: {source_id}")
        directory = self._validated_source_directory(source)
        self._adapter.open(directory)

    def _require_local_desktop_feature(self) -> None:
        if not self._settings.ENABLE_LOCAL_DIRECTORY_OPEN:
            raise FeatureUnavailableError("Local directory opening is disabled")
        if not self._settings.LOCAL_DESKTOP_MODE:
            raise FeatureUnavailableError("Local directory opening requires desktop mode")

    @staticmethod
    def _validated_source_directory(source: KnowledgeSource) -> Path:
        if source.root_path.startswith("\\\\"):
            raise InvalidPathError("Network knowledge source directories cannot be opened")
        if not source.enabled:
            raise PermissionDeniedError("Disabled knowledge source cannot be opened")
        try:
            display_path, normalized_path = normalize_authorized_directory(source.root_path)
        except ValueError as exc:
            raise InvalidPathError("Knowledge source directory is unavailable") from exc
        if normalized_path != source.normalized_root_path:
            # 目录移动或软链目标变化后拒绝打开，避免数据库旧授权被重定向利用。
            raise InvalidPathError("Knowledge source directory authorization changed")
        if Path(display_path).is_symlink() or not os.path.isdir(display_path):
            raise InvalidPathError("Knowledge source directory is unavailable")
        return Path(display_path)
