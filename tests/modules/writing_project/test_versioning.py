from copy import deepcopy

from app.modules.writing_project.schema import GeneratedContent, WritingProjectSnapshot
from app.modules.writing_project.versioning import restore_snapshot, snapshot_content


def _content() -> GeneratedContent:
    return GeneratedContent(
        sections=[{"id": "s1", "title": "背景", "draft": "draft"}],
        citations=[{"pmid": "12345", "locator": "abstract"}],
        pending_items=[
            {
                "id": "p1",
                "text": "核验结论",
                "type": "claim",
                "status": "pending",
                "section_id": "s1",
                "paragraph_id": "p-1",
            }
        ],
    )


def test_snapshot_is_deeply_immutable() -> None:
    content = _content()
    snapshot = snapshot_content(content, version=1, parent_version=None)
    before = deepcopy(snapshot.content)
    content.sections[0].draft = "changed"
    assert snapshot.content == before


def test_restore_creates_new_version_without_mutating_source() -> None:
    source = WritingProjectSnapshot(version=1, parent_version=None, content=_content())
    restored = restore_snapshot(source, next_version=3)
    assert restored.version == 3
    assert restored.parent_version == 1
    assert restored.content == source.content
    assert restored is not source
