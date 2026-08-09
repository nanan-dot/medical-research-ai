from langgraph.types import Command

from app.agents.graph import build_agent_graph
from app.agents.limits import AgentLimits, LimitExceededError


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def test_limits_reject_excessive_tool_calls_and_resource_units() -> None:
    limits = AgentLimits(max_steps=3, max_tool_calls=1, max_resource_units=2)

    limits.assert_allowed(step_count=1, tool_calls=1, resource_units=2, elapsed_seconds=0)

    try:
        limits.assert_allowed(step_count=1, tool_calls=2, resource_units=2, elapsed_seconds=0)
    except LimitExceededError as error:
        assert error.code == "maximum_tool_calls_reached"
    else:
        raise AssertionError("tool-call limit must stop execution")


def test_approval_interrupt_resumes_only_after_explicit_approval() -> None:
    graph = build_agent_graph()
    config = _config("approval-resume")

    paused = graph.invoke(
        {
            "user_query": "Confirm direction",
            "task_type": "evidence_qa",
            "evidence": ["provided source"],
            "pending_confirmations": ["confirm research direction"],
        },
        config=config,
    )

    assert "__interrupt__" in paused
    resumed = graph.invoke(Command(resume={"decision": "approve"}), config=config)
    assert resumed["workflow_status"] == "completed"
    assert resumed["decision"] == "approved"


def test_rejection_and_cancellation_end_without_completion() -> None:
    graph = build_agent_graph()
    config = _config("approval-reject")
    graph.invoke(
        {
            "user_query": "Confirm export",
            "task_type": "writing",
            "pending_confirmations": ["confirm writing export"],
        },
        config=config,
    )

    result = graph.invoke(Command(resume={"decision": "cancel"}), config=config)
    assert result["workflow_status"] == "cancelled"
    assert result["decision"] == "cancelled"
