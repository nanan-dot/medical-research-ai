"""候选研究方向的持久化模型。"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ResearchDirection(Base):
    """一条可编辑、可追溯的候选研究方向。"""

    __tablename__ = "research_directions"
    __table_args__ = (
        Index("ix_research_directions_conditions_id", "research_conditions_id"),
        Index("ix_research_directions_matrix_id", "evidence_matrix_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    research_conditions_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("research_conditions.id"), nullable=False,
    )
    evidence_matrix_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("evidence_matrices.id"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    research_object: Mapped[str] = mapped_column(Text, nullable=False)
    study_type: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    current_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    current_evidence_sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    controversy: Mapped[str] = mapped_column(Text, nullable=False)
    controversy_sources_json: Mapped[str] = mapped_column(Text, nullable=False)
    gap: Mapped[str] = mapped_column(Text, nullable=False)
    novelty_uncertainty: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(32), nullable=False)
    generation_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    methods: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    difficulty: Mapped[str | None] = mapped_column(Text)
    time_risk: Mapped[str | None] = mapped_column(Text)
    resource_risk: Mapped[str | None] = mapped_column(Text)
    ethics_risk: Mapped[str | None] = mapped_column(Text)
    search_terms: Mapped[str | None] = mapped_column(Text)
    advisor_questions: Mapped[str | None] = mapped_column(Text)
    generation_metadata_json: Mapped[str] = mapped_column(Text, nullable=False)
    merged_from_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    merged_into_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("research_directions.id"), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
