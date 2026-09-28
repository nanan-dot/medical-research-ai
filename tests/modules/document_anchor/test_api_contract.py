"""真实 HTTP 状态与任务中心集成，不伪造 API 返回。"""

import hashlib

from app.core.config import settings


def test_unavailable_conflict_and_safe_capability_response(api_context, monkeypatch):
    client, document_id, path = api_context
    url = f"/api/v1/documents/{document_id}/anchor-revisions"
    assert client.post(url, json={"expected_file_hash": "f" * 64}).status_code == 409
    monkeypatch.setattr(
        settings, "PDF_TEXTITEM_EXTRACTOR_COMMAND", '["nonexistent-a0-tool"]'
    )
    response = client.post(
        url, json={"expected_file_hash": hashlib.sha256(path.read_bytes()).hexdigest()}
    )
    assert response.status_code == 503
    assert str(path) not in response.text and "nonexistent-a0-tool" not in response.text
    assert client.get("/api/v1/document-anchor-capability").status_code == 503


def test_http_cancellation_and_revision_scope(api_context):
    client, document_id, path = api_context
    revision = client.post(
        f"/api/v1/documents/{document_id}/anchor-revisions",
        json={"expected_file_hash": hashlib.sha256(path.read_bytes()).hexdigest()},
    ).json()
    response = client.post(f"/api/v1/tasks/{revision['task_id']}/cancel")
    assert response.status_code == 200
    assert (
        client.get(f"/api/v1/document-anchor-revisions/{revision['id']}").json()[
            "state"
        ]
        == "cancelled"
    )
    assert (
        client.get(
            f"/api/v1/document-anchor-revisions/{revision['id']}/pages/1/quality"
        ).status_code
        == 404
    )
    assert client.get("/api/v1/document-anchor-revisions/99999").status_code == 404
    assert (
        client.get("/api/v1/document-anchor-capability").json()["status"] == "AVAILABLE"
    )
