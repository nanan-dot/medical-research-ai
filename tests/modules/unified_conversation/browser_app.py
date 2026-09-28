"""浏览器验收专用应用：真实路由/事务，隔离数据库和确定性服务替身。"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import Depends, FastAPI
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.common.exception_handlers import app_error_handler
from app.common.exceptions import AppError
from app.core.database import Base, _enable_sqlite_foreign_keys, get_session
from app.integrations.llm.exceptions import LLMConnectionError
from app.modules.document.router import router as document_router
from app.modules.unified_conversation.general_answer_service import GeneralAnswer
from app.modules.unified_conversation.paper_answer_service import PaperAnswerService
from app.modules.unified_conversation.query_router import QueryRouter
from app.modules.unified_conversation.router import chat_service, router
from app.modules.unified_conversation.schema import AnswerContent, UnifiedAnswerSection
from app.modules.unified_conversation.service import UnifiedConversationService
from tests.modules.unified_conversation.test_acceptance import (
    PaperClient,
    document,
    evidence,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    with TemporaryDirectory(prefix="unified-chat-browser-") as directory:
        root = Path(directory)
        engine = create_async_engine(
            "sqlite+aiosqlite:///" + (root / "isolated.db").as_posix()
        )
        event.listen(engine.sync_engine, "connect", _enable_sqlite_foreign_keys)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        app.state.sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with app.state.sessions() as session:
            await document(session, root)
        yield
        await engine.dispose()


app = FastAPI(lifespan=lifespan)
app.add_exception_handler(AppError, app_error_handler)
app.include_router(router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")


async def isolated_session():
    async with app.state.sessions() as session:
        try:
            yield session
            await session.commit()
        except BaseException:
            await session.rollback()
            raise


class BrowserGeneral:
    async def answer(self, question, history):
        if question == "您好":
            await asyncio.sleep(10)
        if question == "服务故障":
            raise LLMConnectionError("deterministic test failure")
        return GeneralAnswer("验收替身：通用回答。未调用真实模型。", "browser-test")


class BrowserPaper(PaperClient):
    async def ask(self, index, question):
        self.calls.append((index, question))
        return evidence(empty="不足" in question)


class BrowserExternal:
    async def answer(self, query):
        return AnswerContent(
            sections=[
                UnifiedAnswerSection(
                    source_type="web_augmented", content="验收替身：外部检索词 " + query
                )
            ],
            warnings=["pubmed_metadata_or_abstract_only"],
        )


async def isolated_chat(session: AsyncSession = Depends(get_session)):  # noqa: B008
    return UnifiedConversationService(
        session,
        general_answer_service=BrowserGeneral(),
        query_router=QueryRouter(),
        paper_answer_service=PaperAnswerService(
            session, client_factory=lambda: BrowserPaper([])
        ),
        external_answer_service=BrowserExternal(),
    )


app.dependency_overrides[get_session] = isolated_session
app.dependency_overrides[chat_service] = isolated_chat
