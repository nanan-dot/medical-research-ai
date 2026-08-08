"""不可变写作快照的纯函数。"""

from app.modules.writing_project.schema import (
    GeneratedContent,
    WritingProjectSnapshot,
)


def snapshot_content(
    content: GeneratedContent,
    *,
    version: int,
    parent_version: int | None,
) -> WritingProjectSnapshot:
    """通过序列化复制隔离可变嵌套对象，避免历史版本被后续编辑污染。"""
    return WritingProjectSnapshot(
        version=version,
        parent_version=parent_version,
        content=GeneratedContent.model_validate(content.model_dump(mode="json")),
    )


def restore_snapshot(
    source: WritingProjectSnapshot,
    *,
    next_version: int,
) -> WritingProjectSnapshot:
    return snapshot_content(
        source.content,
        version=next_version,
        parent_version=source.version,
    )
