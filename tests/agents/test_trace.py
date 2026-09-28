from fastapi.testclient import TestClient

from app.agents.trace import MAX_SUMMARY_LENGTH, summarize
from app.main import app


def test_trace_summary_redacts_secrets_and_truncates_text() -> None:
    summary = summarize("api_key=secret-value sk-example " + "x" * 300)

    assert "secret-value" not in summary
    assert "sk-example" not in summary
    assert "[REDACTED]" in summary
    assert len(summary) == MAX_SUMMARY_LENGTH


def test_legacy_trace_runtime_rejects_new_json_run_writes() -> None:
    with TestClient(app) as client:
        started = client.post(
            "/api/v1/agent/runs",
            json={
                "query": "Review provided source",
            },
        )
    assert started.status_code == 410
    assert started.json()["detail"] == "legacy_agent_run_writes_retired"


def test_unknown_trace_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/agent/runs/not-found/trace")

    assert response.status_code == 404
