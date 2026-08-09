"""Offline service tests for evidence-analysis metadata and empty matrices."""

import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import ConflictError
from app.core import models  # noqa: F401  # register all ORM tables for test metadata
from app.core.database import Base
from app.modules.evidence_analysis.schema import EvidenceAnalysisRequest
from app.modules.evidence_analysis.service import EvidenceAnalysisService
from app.modules.evidence_matrix.model import EvidenceMatrix, MatrixCell, MatrixDocument


@pytest.fixture
async def session(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'analysis.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def test_empty_matrix_is_rejected_before_model_generation(session) -> None:
    matrix = EvidenceMatrix(name="空矩阵", description="", status="draft", version=1)
    session.add(matrix)
    await session.flush()
    service = EvidenceAnalysisService(session)

    with pytest.raises(ConflictError, match="empty"):
        await service.analyze(
            EvidenceAnalysisRequest(matrix_id=matrix.id, retrieval_scope="PubMed: EGFR")
        )


async def test_analysis_returns_required_retrieval_metadata(session) -> None:
    matrix = EvidenceMatrix(name="矩阵", description="", status="active", version=7)
    session.add(matrix)
    await session.flush()
    session.add(MatrixDocument(matrix_id=matrix.id, document_id=11))
    session.add(
        MatrixCell(
            matrix_id=matrix.id,
            document_id=11,
            field_key="intervention",
            cell_value="EGFR 抑制剂",
            sources=json.dumps([{"pmid": "12345", "locator": "abstract"}]),
            generated_value="EGFR 抑制剂",
            user_value=None,
            status="generated",
        )
    )
    session.add(
        MatrixCell(
            matrix_id=matrix.id,
            document_id=11,
            field_key="study_type",
            cell_value="队列",
            sources="[]",
            generated_value=None,
            user_value="队列",
            status="user_edited",
        )
    )
    await session.flush()

    async def fake_generator(
        prompt: str, model_config_id: int | None, has_private_notes: bool
    ) -> str:
        assert "检索" in prompt
        assert model_config_id is None
        assert has_private_notes is False
        return json.dumps(
            {
                "consistencies": [
                    {
                        "statement": "当前检索结果中的该主题需谨慎解读。",
                        "confidence": "low",
                        "evidence": [{"pmid": "12345", "locator": "abstract"}],
                        "statistics_basis": [
                            "主题 EGFR 抑制剂: 1 篇, 趋势 insufficient"
                        ],
                        "research_types": ["队列"],
                    }
                ],
                "conflicts": [],
                "limitations": [],
                "gaps": [],
                "search_questions": [],
            }
        )

    result = await EvidenceAnalysisService(
        session, interpretation_generator=fake_generator
    ).analyze(
        EvidenceAnalysisRequest(
            matrix_id=matrix.id,
            retrieval_scope="PubMed: EGFR",
            retrieval_date="2026-08-08",
        )
    )

    assert result.metadata.retrieval_scope == "PubMed: EGFR"
    assert str(result.metadata.retrieval_date) == "2026-08-08"
    assert result.metadata.matrix_version == 7
    assert result.metadata.document_count == 1
