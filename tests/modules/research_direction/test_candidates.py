"""R3-WP04 离线测试：不调用云端模型，也不伪造外部文献。"""

import json

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.common.exceptions import AIModelError, ConflictError, NotFoundError
from app.core import models  # noqa: F401  # 注册全部表，确保外键可建。
from app.core.database import Base
from app.modules.evidence_matrix.model import EvidenceMatrix, MatrixCell, MatrixDocument
from app.modules.research_conditions.model import (
    ResearchConditions,
    ResearchConditionsVersion,
)
from app.modules.research_direction.schema import (
    ResearchDirectionGenerateRequest,
    ResearchDirectionPatch,
)
from app.modules.research_direction.service import ResearchDirectionService


@pytest.fixture
async def session(tmp_path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'directions.db').as_posix()}"
    )
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with factory() as database_session:
        yield database_session
    await engine.dispose()


async def _seed_inputs(session) -> tuple[int, int]:
    conditions = ResearchConditions(current_version=1)
    session.add(conditions)
    await session.flush()
    session.add(
        ResearchConditionsVersion(
            conditions_id=conditions.id,
            version=1,
            conditions_json=json.dumps(
                {"specialty": {"value": "肿瘤学", "known": True, "source": "user"}}
            ),
            uncertain_notes=None,
        )
    )
    matrix = EvidenceMatrix(
        name="EGFR 矩阵", description="", status="active", version=3
    )
    session.add(matrix)
    await session.flush()
    for document_id, topic, pmid in (
        (11, "EGFR 抑制剂", "12345"),
        (12, "耐药机制", "67890"),
    ):
        session.add(MatrixDocument(matrix_id=matrix.id, document_id=document_id))
        session.add(
            MatrixCell(
                matrix_id=matrix.id,
                document_id=document_id,
                field_key="topic",
                cell_value=topic,
                sources=json.dumps([{"pmid": pmid, "locator": "abstract"}]),
                generated_value=topic,
                user_value=None,
                status="generated",
            )
        )
    await session.flush()
    return conditions.id, matrix.id


def _candidate(name: str, pmid: str, strategy: str) -> dict[str, object]:
    source = {"pmid": pmid, "locator": "abstract"}
    return {
        "name": name,
        "question": f"{name} 在限定肿瘤人群中的关联是什么？",
        "research_object": "接受 EGFR 靶向治疗的肺癌患者",
        "study_type": "回顾性队列研究",
        "evidence": [{"statement": "矩阵中记录了相关主题。", "source": source}],
        "current_evidence": {"text": "当前矩阵包含相关报道。", "sources": [source]},
        "controversy": {"text": "结局定义存在差异。", "sources": [source]},
        "gap": "该组合在当前检索结果中较少见，需继续检索确认。",
        "novelty_uncertainty": "新颖性需由导师与补充检索确认。",
        "priority": "medium",
        "generation_strategy": strategy,
        "missing_evidence": False,
    }


async def _fake_generator(
    prompt: str, model_config_id: int | None, has_private_data: bool
) -> str:
    assert has_private_data is True
    if "methods" in prompt:
        return json.dumps(
            {
                "methods": "回顾性收集并预注册分析方案。",
                "requirements": "样本来源和设备条件需确认。",
                "difficulty": "中等。",
                "time_risk": "入组与清洗可能延迟。",
                "resource_risk": "数据访问权限需确认。",
                "ethics_risk": "需确认伦理审批与脱敏要求。",
                "search_terms": "(EGFR[Title/Abstract]) AND resistance[Title/Abstract]",
                "advisor_questions": "主要结局与可获得样本量是否合适？",
            }
        )
    return json.dumps(
        [
            _candidate("EGFR 耐药分层", "12345", "gap-based"),
            _candidate("EGFR 与耐药机制交叉", "67890", "cross-topic"),
            _candidate("EGFR 结局定义比较", "12345", "gap-based"),
        ]
    )


async def test_generate_details_merge_delete_and_version(session) -> None:
    conditions_id, matrix_id = await _seed_inputs(session)
    service = ResearchDirectionService(session, model_generator=_fake_generator)
    generated = await service.generate(
        ResearchDirectionGenerateRequest(
            research_conditions_id=conditions_id, evidence_matrix_id=matrix_id
        )
    )
    assert len(generated) == 3
    assert any(item.generation_strategy == "cross-topic" for item in generated)
    assert all(
        item.methods is None and item.current_evidence.sources for item in generated
    )

    cached = await service.get_details(generated[0].id)
    assert cached.methods is None
    expanded = await service.generate_details(generated[0].id, None)
    assert expanded.methods is not None and "[Title/Abstract]" in expanded.search_terms
    cached_after = await service.get_details(generated[0].id)
    assert cached_after.methods == expanded.methods

    merged = await service.patch(
        generated[0].id,
        ResearchDirectionPatch(priority="high", merge_source_ids=[generated[1].id]),
    )
    source = await service.get(generated[1].id)
    assert (
        merged.version == 2
        and source.status == "merged"
        and source.merged_into_id == merged.id
    )
    await service.delete(generated[2].id)
    with pytest.raises(NotFoundError):
        await service.get(generated[2].id)


async def test_rejects_ungrounded_and_duplicate_candidates(session) -> None:
    conditions_id, matrix_id = await _seed_inputs(session)

    async def invalid_generator(*_args) -> str:
        result = [_candidate("重复方向", "99999", "gap-based")] * 3
        return json.dumps(result)

    service = ResearchDirectionService(session, model_generator=invalid_generator)
    with pytest.raises(AIModelError):
        await service.generate(
            ResearchDirectionGenerateRequest(
                research_conditions_id=conditions_id, evidence_matrix_id=matrix_id
            )
        )


async def test_merge_rejects_cross_matrix_sources(session) -> None:
    conditions_id, matrix_id = await _seed_inputs(session)
    service = ResearchDirectionService(session, model_generator=_fake_generator)
    generated = await service.generate(
        ResearchDirectionGenerateRequest(
            research_conditions_id=conditions_id, evidence_matrix_id=matrix_id
        )
    )
    with pytest.raises(ConflictError, match="itself"):
        await service.patch(
            generated[0].id, ResearchDirectionPatch(merge_source_ids=[generated[0].id])
        )
