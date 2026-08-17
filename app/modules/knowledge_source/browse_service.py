"""Windows native directory picker for knowledge-source authorization."""

from __future__ import annotations

from app.common.exceptions import (
    AppError,
    PermissionDeniedError,
    TemporarilyUnavailableError,
)
from app.modules.knowledge_source.service import (
    KnowledgeSourcePathError,
    normalize_authorized_directory,
)

DIRECTORY_PICKER_UNAVAILABLE_MESSAGE = "当前环境无法弹出目录选择器，请手动输入路径"


class DirectoryPickerUnavailableError(AppError):
    """系统目录选择器不可用时，向调用方提供不含本地路径的错误。"""

    status_code = 400
    code = "directory_picker_unavailable"


def select_authorized_directory() -> str | None:
    """打开 Windows 文件夹选择器并返回经校验的绝对路径。

    Returns:
        用户确认的规范化绝对路径；取消时返回 ``None``。

    Raises:
        DirectoryPickerUnavailableError: 无桌面会话或所选目录不可访问时抛出。
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError as exc:
        raise DirectoryPickerUnavailableError(
            DIRECTORY_PICKER_UNAVAILABLE_MESSAGE
        ) from exc

    root: tk.Tk | None = None
    try:
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected_path = filedialog.askdirectory(title="选择资料文件夹")
    except (tk.TclError, OSError, RuntimeError) as exc:
        raise DirectoryPickerUnavailableError(
            DIRECTORY_PICKER_UNAVAILABLE_MESSAGE
        ) from exc
    finally:
        if root is not None:
            root.destroy()

    if not selected_path:
        return None

    try:
        display_path, _ = normalize_authorized_directory(selected_path)
    except (
        KnowledgeSourcePathError,
        PermissionDeniedError,
        TemporarilyUnavailableError,
    ) as exc:
        raise DirectoryPickerUnavailableError(
            DIRECTORY_PICKER_UNAVAILABLE_MESSAGE
        ) from exc
    return display_path
