"""复用 PaperQA2 适配器，查询结果交由统一轮次事务保存。"""

import asyncio
from collections.abc import Callable
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AppError
from app.common.hashing import sha256_file
from app.integrations.llm.exceptions import LLMClientError
from app.integrations.paperqa2 import PaperDocument, PaperQA2Client, PaperQAAnswer
from app.integrations.paperqa2.exceptions import (
    PaperQA2Error,
    PaperQA2IndexNotFoundError,
)
from app.modules.document.model import Document
from app.modules.document.service import DocumentService
from app.modules.unified_conversation.answer_policy import paper_section
from app.modules.unified_conversation.model_client import paper_client
from app.modules.unified_conversation.schema import AnswerContent, UnifiedAnswerSection

# 取消 asyncio 等待不能停止 PaperQA2 的工作线程。保留任务直到线程结束，限制残留工作总量。
_ACTIVE_QUERIES: set[asyncio.Task[PaperQAAnswer]] = set()
MAX_ACTIVE_QUERIES = 2


async def query_with_recovery(
    client: PaperQA2Client, document: Document, path: Path, question: str
) -> PaperQAAnswer:
    try:
        return await client.ask(document.paperqa_index_key or "", question)
    except PaperQA2IndexNotFoundError:
        actual_hash = await asyncio.to_thread(sha256_file, path)
        if actual_hash != document.file_hash:
            raise PaperQA2Error("源文献发生变化，请重新索引") from None
        index = await client.index_documents(
            [PaperDocument(path=path, title=document.parsed_title)]
        )
        return await client.ask(index, question)


def _release(task: asyncio.Task[PaperQAAnswer]) -> None:
    _ACTIVE_QUERIES.discard(task)
    if not task.cancelled():
        task.exception()


class PaperAnswerService:
    def __init__(
        self,
        session: AsyncSession,
        client_factory: Callable[[], PaperQA2Client] | None = None,
        timeout: float = 280.0,
    ) -> None:
        self.session = session
        self.client_factory = client_factory
        self.timeout = timeout

    async def answer(self, question: str, document_ids: list[int]) -> AnswerContent:
        result = AnswerContent()
        client: PaperQA2Client | None = None
        for document_id in document_ids:
            document = await self.session.get(Document, document_id)
            if document is None:
                raise ValueError("范围校验必须先于文献执行")
            issue = self._readiness(document)
            if issue:
                result.warnings.append(issue)
                result.sections.append(
                    UnifiedAnswerSection(
                        source_type="paper_grounded",
                        answer_status="failed",
                        content=f"文献 {document_id} 尚未准备就绪，请在文档详情中检查解析和索引状态。",
                    )
                )
                continue
            try:
                if len(_ACTIVE_QUERIES) >= MAX_ACTIVE_QUERIES:
                    raise TimeoutError("PaperQA2 worker capacity reached")
                client = client or (
                    self.client_factory()
                    if self.client_factory
                    else await paper_client(self.session)
                )
                await self.session.refresh(document, attribute_names=["asset"])
                path = await DocumentService(self.session)._source_file_path(document)
                prompt = (
                    "仅依据当前索引论文回答；保持用户语言。无法确定的部分明确指出，不编造事实。问题："
                    + question
                )
                task = asyncio.create_task(
                    query_with_recovery(client, document, path, prompt)
                )
                _ACTIVE_QUERIES.add(task)
                task.add_done_callback(_release)
                answer = await asyncio.wait_for(asyncio.shield(task), self.timeout)
                section = paper_section(document_id, answer)
                result.sections.append(section)
                result.scope_used.append(document_id)
                if section.answer_status != "answered":
                    result.warnings.append(
                        "partial_evidence"
                        if section.answer_status == "partial"
                        else "insufficient_evidence"
                    )
                if any(
                    term in answer.answer.casefold()
                    for term in ("来源冲突", "conflicting evidence")
                ):
                    result.warnings.append("source_conflict")
            except (PaperQA2Error, AppError, LLMClientError, TimeoutError, OSError):
                result.warnings.append("retrieval_failure")
                result.sections.append(
                    UnifiedAnswerSection(
                        source_type="paper_grounded",
                        answer_status="failed",
                        content=f"文献 {document_id} 的检索服务未能完成请求，请重试。",
                    )
                )
        statuses = [section.answer_status for section in result.sections]
        if (
            statuses
            and all(status == "answered" for status in statuses)
            and "source_conflict" not in result.warnings
        ):
            result.status = "answered"
        elif any(status in {"answered", "partial"} for status in statuses):
            result.status = "partial"
        else:
            result.status = (
                "failed" if "failed" in statuses else "insufficient_evidence"
            )
        if len(document_ids) > 1:
            result.warnings.append("selected_documents_separate_results")
        if result.status != "answered":
            result.actions = ["select_documents", "open_documents", "retry"]
        result.warnings = list(dict.fromkeys(result.warnings))
        return result

    @staticmethod
    def _readiness(document: Document) -> str | None:
        if document.parse_status == "failed":
            return "parse_failure"
        if document.parse_status != "succeeded":
            return "index_not_ready"
        if document.index_status == "failed":
            return "index_failure"
        if (
            document.index_status != "succeeded"
            or not document.paperqa_index_key
            or document.indexed_hash != document.file_hash
        ):
            return "index_not_ready"
        return None
