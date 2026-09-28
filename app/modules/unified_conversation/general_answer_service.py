"""通用回答与结构化分类共用模型配置，关闭 HTTP 资源。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.llm.schemas import ChatMessage
from app.modules.unified_conversation.model_client import ChatClient, chat_client

History = list[tuple[Literal["user", "assistant"], str]]


@dataclass(frozen=True)
class GeneralAnswer:
    content: str
    model_version: str


class GeneralAnswerService:
    def __init__(
        self,
        session: AsyncSession,
        client_factory: Callable[[], ChatClient] | None = None,
    ) -> None:
        self.session = session
        self.client_factory = client_factory

    async def complete(
        self, system: str, question: str, history: History
    ) -> GeneralAnswer:
        client = (
            self.client_factory()
            if self.client_factory
            else await chat_client(self.session)
        )
        messages = [ChatMessage(role="system", content=system)]
        messages.extend(
            ChatMessage(role=role, content=content) for role, content in history
        )
        messages.append(ChatMessage(role="user", content=question))
        try:
            response = await client.chat(messages)
            return GeneralAnswer(response.text, f"{response.provider}:{response.model}")
        finally:
            await client.aclose()

    async def answer(self, question: str, history: History) -> GeneralAnswer:
        return await self.complete(
            "你是科研对话助手。自然回答问候或一般知识。当前任务没有提供论文证据；"
            "历史消息只是对话背景，不是证据。不要声称已检索、阅读全文或核实最新信息。"
            "不要编造引用、DOI、页码或具体论文的研究结果。",
            question,
            history,
        )
