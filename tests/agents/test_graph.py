from app.agents.graph import EVIDENCE_ERROR, MAX_STEPS_ERROR, build_agent_graph


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def test_local_evidence_path_completes_and_persists_checkpoint() -> None:
    graph = build_agent_graph()
    config = _config("local-evidence")

    result = graph.invoke(
        {
            "user_query": "What evidence is available?",
            "task_type": "evidence_qa",
            "evidence": ["document-17: relevant excerpt"],
        },
        config=config,
    )

    snapshot = graph.get_state(config)
    assert result["workflow_status"] == "completed"
    assert "local_search_completed" in result["search_history"]
    assert snapshot.values["workflow_status"] == "completed"


def test_external_search_path_fails_without_inventing_evidence() -> None:
    graph = build_agent_graph()

    result = graph.invoke(
        {
            "user_query": "Find new literature",
            "task_type": "literature_search",
            "needs_external_search": True,
        },
        config=_config("external-search"),
    )

    assert result["workflow_status"] == "failed"
    assert "pubmed_search_completed" in result["search_history"]
    assert result["evidence"] == []
    assert EVIDENCE_ERROR in result["errors"]


def test_writing_path_preserves_caller_draft_without_generation() -> None:
    graph = build_agent_graph()

    result = graph.invoke(
        {
            "user_query": "Review this draft",
            "task_type": "writing",
            "draft": "Caller supplied draft.",
        },
        config=_config("writing"),
    )

    assert result["workflow_status"] == "completed"
    assert result["draft"] == "Caller supplied draft."


def test_pending_confirmation_stops_before_completion() -> None:
    graph = build_agent_graph()

    result = graph.invoke(
        {
            "user_query": "Confirm scope",
            "task_type": "evidence_qa",
            "evidence": ["provided source"],
            "pending_confirmations": ["confirm scope"],
        },
        config=_config("confirmation"),
    )

    assert result["workflow_status"] == "awaiting_confirmation"


def test_maximum_step_limit_ends_workflow() -> None:
    graph = build_agent_graph()

    result = graph.invoke(
        {
            "user_query": "Limited work",
            "task_type": "evidence_qa",
            "max_steps": 1,
        },
        config=_config("maximum-steps"),
    )

    assert result["workflow_status"] == "failed"
    assert MAX_STEPS_ERROR in result["errors"]
