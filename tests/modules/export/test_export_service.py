from datetime import UTC, datetime

import pytest

from app.common.exceptions import ConflictError, NotFoundError
from app.modules.conversation.model import Citation, Conversation, Message
from app.modules.conversation.service import ConversationService
from app.modules.document.model import Document
from app.modules.export.schema import MarkdownExportCreate
from app.modules.export.service import ExportService
from app.modules.knowledge_source.model import KnowledgeSource


async def conversation_fixture(session, tmp_path):
    source = KnowledgeSource(
        name="source",
        source_type="local_folder",
        root_path=str(tmp_path),
        normalized_root_path=str(tmp_path),
        enabled=True,
        sync_status="idle",
    )
    session.add(source)
    await session.flush()
    now = datetime.now(UTC)
    doc = Document(
        knowledge_source_id=source.id,
        file_path="paper.pdf",
        normalized_file_path="paper.pdf",
        file_hash="a" * 64,
        file_size=1,
        modified_time=now,
        modified_time_ns=1,
        scan_state="pending",
    )
    session.add(doc)
    await session.flush()
    conversation = Conversation(
        document_ids=f"[{doc.id}]", title="中文会话", created_at=now, updated_at=now
    )
    session.add(conversation)
    await session.flush()
    user = Message(
        conversation_id=conversation.id,
        sequence=1,
        role="user",
        content="关键数字？",
        created_at=now,
    )
    session.add(user)
    await session.flush()
    assistant = Message(
        conversation_id=conversation.id,
        sequence=2,
        role="assistant",
        content="共 120 人 *需核对*",
        model_version="local:test",
        created_at=now,
    )
    session.add(assistant)
    await session.flush()
    session.add(
        Citation(
            message_id=assistant.id,
            document_id=doc.id,
            evidence_type="paperqa",
            page=None,
            citation_text="真实来源",
            evidence_text="120 participants",
        )
    )
    await session.flush()
    return conversation, doc


@pytest.mark.asyncio
async def test_chinese_filename_repeat_export_and_citations(session, tmp_path):
    conversation, _ = await conversation_fixture(session, tmp_path)
    service = ExportService(session, output_dir=tmp_path / "导出")
    request = MarkdownExportCreate(
        export_type="conversation",
        source_id=conversation.id,
        filename="中文：问答",
        user_notes="我的 *备注*",
    )
    first = await service.create(request)
    second = await service.create(request)
    assert first.filename == "中文：问答.md" and second.filename == "中文：问答-2.md"
    content = (await service.path(first.id)).read_text(encoding="utf-8")
    assert (
        "真实来源" in content and "120 participants" in content and "第 " not in content
    )
    assert "我的 \\*备注\\*" in content and "local:test" == first.model_info


@pytest.mark.asyncio
async def test_path_traversal_and_unwritable_output_are_rejected(session, tmp_path):
    conversation, _ = await conversation_fixture(session, tmp_path)
    with pytest.raises(ValueError):
        await ExportService(session, output_dir=tmp_path / "out").create(
            MarkdownExportCreate(
                export_type="conversation", source_id=conversation.id, filename=".."
            )
        )
    blocked = tmp_path / "blocked"
    blocked.write_text("file", encoding="utf-8")
    with pytest.raises(ConflictError, match="not writable"):
        await ExportService(session, output_dir=blocked).create(
            MarkdownExportCreate(export_type="conversation", source_id=conversation.id)
        )


@pytest.mark.asyncio
async def test_conversation_history_and_delete_do_not_delete_document(
    session, tmp_path
):
    conversation, doc = await conversation_fixture(session, tmp_path)
    service = ConversationService(session)
    assert (await service.get(conversation.id)).messages[1].citations[
        0
    ].citation_text == "真实来源"
    assert (await service.list())[0].message_count == 2
    await service.delete(conversation.id)
    with pytest.raises(NotFoundError):
        await service.get(conversation.id)
    assert await session.get(Document, doc.id) is not None
