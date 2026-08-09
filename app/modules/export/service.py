import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import ConflictError, NotFoundError
from app.core.config import settings
from app.modules.conversation.service import ConversationService
from app.modules.export.markdown_renderer import (
    MAX_EVIDENCE_EXPORT,
    escape_markdown,
    safe_filename,
)
from app.modules.export.model import ExportRecord
from app.modules.export.schema import ExportRead, ExportType, MarkdownExportCreate
from app.modules.paper_analysis.service import PaperAnalysisService


class ExportService:
    def __init__(self, session: AsyncSession, *, output_dir: Path | None = None):
        self.session = session
        self.output_dir = (output_dir or settings.EXPORT_DIR).resolve()

    async def create(self, request: MarkdownExportCreate):
        generated = datetime.now(UTC)
        pending = []
        model_info = None
        if request.export_type == ExportType.ANALYSIS:
            analysis = await PaperAnalysisService(self.session).get(request.source_id)
            content = await PaperAnalysisService(self.session).export_markdown(
                request.source_id
            )
            pending = analysis.pending_confirmations
            model_info = analysis.model_version
        else:
            conversation = await ConversationService(self.session).get(
                request.source_id
            )
            content = self._conversation_markdown(conversation)
            model_info = next(
                (
                    m.model_version
                    for m in reversed(conversation.messages)
                    if m.model_version
                ),
                None,
            )
        content += f"\n## 用户备注\n\n{escape_markdown(request.user_notes or '无')}\n\n生成时间：{generated.isoformat()}\n"
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConflictError("Export directory is not writable") from exc
        stem = safe_filename(request.filename)
        path = self.output_dir / f"{stem}.md"
        counter = 2
        while path.exists():
            path = self.output_dir / f"{stem}-{counter}.md"
            counter += 1
        if path.parent != self.output_dir:
            raise ConflictError("Export path is invalid")
        try:
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise ConflictError("Export file could not be written") from exc
        entity = ExportRecord(
            export_type=request.export_type.value,
            source_ids=json.dumps([request.source_id]),
            generated_at=generated,
            model_info=model_info,
            pending_confirmations=json.dumps(pending),
            local_output_path=str(path),
        )
        self.session.add(entity)
        await self.session.flush()
        return self._read(entity)

    async def get(self, id: int):
        entity = await self.session.get(ExportRecord, id)
        if entity is None:
            raise NotFoundError(f"Export not found: {id}")
        return entity

    async def path(self, id: int):
        entity = await self.get(id)
        path = Path(entity.local_output_path).resolve()
        if path.parent != self.output_dir or not path.is_file():
            raise NotFoundError("Export file is not available")
        return path

    @staticmethod
    def _conversation_markdown(conversation):
        lines = [f"# 论文问答会话 #{conversation.id}", ""]
        for message in conversation.messages:
            lines.extend(
                [
                    f"## {'用户' if message.role == 'user' else '助手'}",
                    "",
                    escape_markdown(message.content),
                    "",
                ]
            )
            for citation in message.citations:
                page = f"，第 {citation.page} 页" if citation.page else ""
                evidence = escape_markdown(
                    (citation.evidence_text or "")[:MAX_EVIDENCE_EXPORT]
                )
                lines.extend(
                    [
                        f"- 来源：{escape_markdown(citation.citation_text or '未命名来源')}{page}",
                        f"  - 证据：{evidence or '未返回摘录'}",
                    ]
                )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _read(entity):
        return ExportRead(
            id=entity.id,
            export_type=entity.export_type,
            source_ids=json.loads(entity.source_ids),
            generated_at=entity.generated_at.isoformat(),
            model_info=entity.model_info,
            pending_confirmations=json.loads(entity.pending_confirmations or "[]"),
            filename=Path(entity.local_output_path).name,
        )
