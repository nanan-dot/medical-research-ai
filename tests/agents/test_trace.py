from fastapi.testclient import TestClient

from app.agents.trace import MAX_SUMMARY_LENGTH, summarize
from app.main import app


def test_trace_summary_redacts_secrets_and_truncates_text() -> None:
    summary = summarize("api_key=secret-value sk-example " + "x" * 300)

    assert "secret-value" not in summary
    assert "sk-example" not in summary
    assert "[REDACTED]" in summary
    assert len(summary) == MAX_SUMMARY_LENGTH


def test_trace_api_returns_approval_events_and_exports_markdown() -> None:
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/agent/runs",
            json={
                "query": "Review provided source",
                "evidence": ["source-1"],
                "confirmations": ["confirm export"],
            },
        )
        run_id = started.json()["run_id"]
        trace = client.get(f"/api/v1/agent/runs/{run_id}/trace")
        approved = client.post(
            f"/api/v1/agent/runs/{run_id}/approve", json={"decision": "approve"}
        )
        exported = client.post(f"/api/v1/agent/runs/{run_id}/export-trace")

    assert started.status_code == 200
    assert trace.status_code == 200
    assert trace.json()[0]["node"] == "graph_start"
    assert approved.json()["workflow_status"] == "completed"
    assert exported.status_code == 200
    assert "# Agent Trace:" in exported.text
    assert "human_approval" in exported.text


def test_unknown_trace_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/agent/runs/not-found/trace")

    assert response.status_code == 404
