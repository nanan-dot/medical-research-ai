import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.agents.classifier import AgentTaskClassifier
from app.agents.schemas import AgentTaskType, TaskDecision
from app.main import app

ROUTING_DATASET_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "evaluation" / "agent_routing.jsonl"
)


def test_routing_evaluation_dataset_matches_expected_routes() -> None:
    classifier = AgentTaskClassifier()
    records = [
        json.loads(line)
        for line in ROUTING_DATASET_PATH.read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert len(records) == 8
    for record in records:
        decision = classifier.classify(record["query"])
        assert decision.task_type.value == record["expected_task_type"]
        assert decision.use_agent is record["expected_use_agent"]


def test_simple_tasks_use_fixed_services_without_agent() -> None:
    classifier = AgentTaskClassifier()

    decision = classifier.classify("请问这篇 PDF 的研究设计是什么？")

    assert decision.task_type is AgentTaskType.SINGLE_PAPER_QA
    assert decision.use_agent is False
    assert decision.required_tools == ["paper_qa"]


def test_each_supported_task_type_has_deterministic_route() -> None:
    classifier = AgentTaskClassifier()
    cases = {
        "查询我的笔记中纳入标准": AgentTaskType.NOTE_QA,
        "检索最新的外部文献": AgentTaskType.EXTERNAL_SEARCH,
        "比较这五篇论文的终点": AgentTaskType.MULTI_PAPER_COMPARISON,
        "寻找一个候选研究方向": AgentTaskType.CANDIDATE_DIRECTION,
        "生成基金申请的写作提纲": AgentTaskType.WRITING_OUTLINE,
    }

    for query, expected_type in cases.items():
        decision = classifier.classify(query)
        assert decision.task_type is expected_type
        assert decision.use_agent is False
        assert decision.clarification_needed is False


def test_complex_cross_task_request_uses_agent_and_whitelisted_tools() -> None:
    decision = AgentTaskClassifier().classify("检索外部文献并比较多篇论文后生成写作提纲")

    assert decision.task_type is AgentTaskType.COMPLEX_RESEARCH
    assert decision.use_agent is True
    assert set(decision.required_tools) == {
        "pubmed_search",
        "comparison_service",
        "outline_service",
        "citation_check",
    }


def test_ambiguous_request_requests_clarification_instead_of_agent() -> None:
    decision = AgentTaskClassifier().classify("帮我处理一下")

    assert decision.clarification_needed is True
    assert decision.use_agent is False
    assert decision.required_tools == []


def test_injected_complex_classifier_requires_high_confidence_complex_decision() -> None:
    classifier = AgentTaskClassifier(
        complex_classifier=lambda _: TaskDecision(
            task_type=AgentTaskType.COMPLEX_RESEARCH,
            use_agent=True,
            required_tools=["citation_check"],
            reason="受控复杂任务分类器建议。",
            confidence=0.95,
        )
    )

    decision = classifier.classify("需要编排一项未命中规则的综合任务")

    assert decision.task_type is AgentTaskType.COMPLEX_RESEARCH
    assert decision.use_agent is True


def test_unsafe_model_decision_falls_back_to_clarification() -> None:
    classifier = AgentTaskClassifier(
        complex_classifier=lambda _: TaskDecision(
            task_type=AgentTaskType.COMPLEX_RESEARCH,
            use_agent=True,
            confidence=0.5,
        )
    )

    decision = classifier.classify("需要编排一项未命中规则的综合任务")

    assert decision.task_type is AgentTaskType.CLARIFICATION
    assert decision.use_agent is False


def test_agent_task_api_exposes_routing_reason_without_running_tools() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/agent/tasks",
            json={"query": "比较这五篇论文的终点"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["task_type"] == "multi_paper_comparison"
    assert body["use_agent"] is False
    assert body["required_tools"] == ["comparison_service"]
    assert body["reason"]
    assert body["confidence"] == 0.98


def test_agent_task_api_rejects_too_short_query() -> None:
    with TestClient(app) as client:
        response = client.post("/api/v1/agent/tasks", json={"query": "x"})

    assert response.status_code == 422
