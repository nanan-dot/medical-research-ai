"""独立轮次及知识缺口，不改变旧会话或引用表结构。"""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UnifiedTurn(Base):
    __tablename__ = "unified_chat_turns"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "request_id", name="uq_unified_turn_request"
        ),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(64))
    fingerprint: Mapped[str] = mapped_column(String(64))
    trace_id: Mapped[str] = mapped_column(String(32))
    active_key: Mapped[int | None] = mapped_column(unique=True)
    deadline: Mapped[float]
    state: Mapped[str] = mapped_column(String(24))
    user_message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE")
    )
    assistant_message_id: Mapped[int | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    response_json: Mapped[str | None] = mapped_column(Text)


class KnowledgeGap(Base):
    __tablename__ = "unified_knowledge_gaps"
    id: Mapped[int] = mapped_column(primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    question: Mapped[str] = mapped_column(Text)
    document_ids: Mapped[str] = mapped_column(Text)
    research_context_id: Mapped[int | None] = mapped_column(
        ForeignKey("research_contexts.id", ondelete="CASCADE")
    )
    occurrences: Mapped[int] = mapped_column(default=1)
