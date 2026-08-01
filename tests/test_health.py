"""FastAPI 应用生命周期与健康接口测试。"""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_health_endpoint_and_lifespan(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(settings, "DATA_DIR", data_dir)

    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
    assert data_dir.is_dir()


def test_swagger_docs_are_available():
    with TestClient(app) as client:
        response = client.get("/docs")

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()
