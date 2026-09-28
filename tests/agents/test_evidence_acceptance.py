"""Agent 工程验收；合成标签不代表医学事实或真实模型结果。"""

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.agents.adapter import AgentEvidenceResult
from app.agents.model import AgentRunRecord
from app.agents.repository import AgentRunRepository
from app.agents.run_service import AgentRunService
from app.rag.citation_mapper import map_citations
from app.rag.schemas import (
    EvidenceConflict,
    EvidenceSet,
    GroundedAnswer,
    GroundedClaim,
    NumericFact,
    QueryPlan,
    RankedEvidence,
    RetrievalTrace,
)


def packet() -> AgentEvidenceResult:
    evidence = EvidenceSet(evidence=[RankedEvidence(
        document_id="fixture-document", chunk_id="fixture-chunk", rank=1,
        source_path="C:/private/fixture.pdf", page_number=2,
        text_original="PRIVATE_SOURCE_TEXT", role="direct",
    )])
    answer = GroundedAnswer(answer="Synthetic engineering claim", claims=[GroundedClaim(
        claim="Synthetic engineering claim", evidence_chunk_ids=["fixture-chunk"],
        citation_ids=["fixture-chunk"],
    )], citations=map_citations(evidence.evidence), trace_id="fixture-trace")
    trace = RetrievalTrace(trace_id="fixture-trace", query_plan=QueryPlan(query="PRIVATE_QUERY"),
                           selected_evidence=evidence, answer=answer)
    return AgentEvidenceResult(evidence=evidence, answer=answer, trace=trace)


class Adapter:
    def __init__(self, result: AgentEvidenceResult) -> None:
        self.result = result
        self.calls = 0

    def execute(self, state: object) -> AgentEvidenceResult:
        self.calls += 1
        return self.result


@pytest.fixture
def repository(tmp_path: Path) -> AgentRunRepository:
    engine = create_engine(f"sqlite:///{tmp_path / 'agent.db'}")
    AgentRunRecord.metadata.create_all(engine, tables=[AgentRunRecord.__table__])
    return AgentRunRepository(engine)


@pytest.mark.parametrize("fault", ["empty", "insufficient", "dangling", "forged", "no_claim",
                                  "unverified", "wrong_fact", "unmarked_numeric"])
def test_rejects_unsafe_evidence(repository: AgentRunRepository, fault: str) -> None:
    result = packet()
    claim = result.answer.claims[0]
    if fault == "empty":
        result.evidence.evidence = []
    elif fault == "insufficient":
        result.evidence.status = "insufficient_evidence"
    elif fault == "dangling":
        claim.evidence_chunk_ids = ["missing"]
    elif fault == "forged":
        result.answer.citations[0].document_id = "forged"
    elif fault == "no_claim":
        result.answer.claims = []
    else:
        claim.claim = "Synthetic value 42 units"
        claim.is_numeric = fault != "unmarked_numeric"
        claim.numeric_fact_ids = ["missing" if fault == "wrong_fact" else "fixture-chunk"]
        result.evidence.numeric_facts = [NumericFact(metric="fixture", value="42", unit="units",
            population="fixture", source_chunk_id="fixture-chunk", verified=fault != "unverified")]
    _, state = AgentRunService(allow_legacy_writes=True, repository=repository, adapter=Adapter(result)).start({"user_query": "PRIVATE_QUERY"})
    assert state["workflow_status"] == "failed"
    assert state["errors"]


@pytest.mark.parametrize("task,publish,conflict", [("writing", False, False),
    ("research_direction", False, False), ("evidence_qa", True, False), ("evidence_qa", False, True)])
def test_required_approval(repository: AgentRunRepository, task: str, publish: bool, conflict: bool) -> None:
    result = packet()
    if conflict:
        result.evidence.conflicts = [EvidenceConflict(metric="fixture", population="fixture",
                                                    source_chunk_ids=["fixture-chunk"])]
    service = AgentRunService(allow_legacy_writes=True, repository=repository, adapter=Adapter(result))
    run_id, state = service.start({"user_query": "query", "task_type": task, "publish_requested": publish})
    assert state["workflow_status"] == "awaiting_confirmation"
    payload = state["approval_payload"]
    assert {"task_type", "evidence_status", "citations", "limitations", "actions"} <= payload.keys()
    assert service.resume(run_id, "approve")["workflow_status"] == "completed"


@pytest.mark.parametrize("decision,status", [("reject", "rejected"), ("cancel", "cancelled")])
def test_stop_decisions(repository: AgentRunRepository, decision: str, status: str) -> None:
    adapter = Adapter(packet())
    service = AgentRunService(allow_legacy_writes=True, repository=repository, adapter=adapter)
    run_id, _ = service.start({"user_query": "query", "task_type": "writing"})
    state = service.resume(run_id, decision)
    assert state["workflow_status"] == status
    events = service.get_trace(run_id)
    assert "citation_check" not in [event.node for event in events]
    assert events[-1].approval == decision
    assert adapter.calls == 1
    with pytest.raises(ValueError):
        service.resume(run_id, "approve")


def test_persistent_replay(repository: AgentRunRepository) -> None:
    service = AgentRunService(allow_legacy_writes=True, repository=repository, adapter=Adapter(packet()))
    run_id, _ = service.start({"user_query": "PRIVATE_QUERY", "task_type": "writing"})
    rebuilt = AgentRunService(allow_legacy_writes=True, repository=repository)
    assert rebuilt.get(run_id)["workflow_status"] == "awaiting_confirmation"
    state = rebuilt.resume(run_id, "approve")
    assert state["workflow_status"] == "completed"
    restarted = AgentRunService(allow_legacy_writes=True, repository=repository)
    assert restarted.get(run_id)["decision"] == "approved"
    events = restarted.get_trace(run_id)
    assert {"retrieve_evidence", "evidence_check", "citation_check"} <= {event.node for event in events}
    source_event = next(event for event in events if event.node == "evidence_check")
    assert source_event.trace_id == "fixture-trace"
    assert source_event.sources[0]["chunk_id"] == "fixture-chunk"
    exported = str([event.to_dict() for event in events])
    assert "PRIVATE_QUERY" not in exported and "PRIVATE_SOURCE_TEXT" not in exported
    assert "C:/private" not in exported
    assert restarted.get_retrieval_trace(run_id)["trace_id"] == "fixture-trace"


def test_default_adapter_fails_closed(repository: AgentRunRepository) -> None:
    _, state = AgentRunService(allow_legacy_writes=True, repository=repository).start({"user_query": "query"})
    assert state["workflow_status"] == "failed"
    assert "adapter_unavailable" in state["errors"]


def test_api_contract(repository: AgentRunRepository) -> None:
    from app.agents.router import get_run_service, router
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_run_service] = lambda: AgentRunService(allow_legacy_writes=True, repository=repository, adapter=Adapter(packet()))
    with TestClient(app) as client:
        assert client.post("/agent/runs", json={"query": "x"}).status_code == 422
        assert client.post("/agent/runs", json={"query": "query", "evidence": ["forged"]}).status_code == 422
        assert client.get("/agent/runs/missing").status_code == 404
        started = client.post("/agent/runs", json={"query": "query", "task_type": "writing"})
        assert started.status_code == 410
        assert started.json()["detail"] == "legacy_agent_run_writes_retired"
