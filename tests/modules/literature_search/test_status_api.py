from fastapi.testclient import TestClient

from app.main import app


def test_status_api_never_marks_unverified_record_retracted():
    with TestClient(app) as client:
        response = client.post("/api/v1/literature-status/check", json={"verified": False, "is_retracted": True})
    assert response.status_code == 200
    assert response.json()["status"] == "unknown" and response.json()["persistent"] is False
