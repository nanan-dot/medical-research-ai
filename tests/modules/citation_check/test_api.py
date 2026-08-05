"""citation_check API 接口测试。

使用 FastAPI TestClient，monkeypatch service 模块中的 CitationVerifier，
避免真实网络调用；验证路由、请求/响应模型与审计报告结构。
"""

from fastapi.testclient import TestClient

from app.main import app


class _FakeVerifier:
    """替身校验器：把请求文本中的每个引用都标为 verified=true。"""

    async def verify_item(self, item):
        item.verified = True
        item.verified_by = "pubmed"
        item.verified_on = "2026-08-05T00:00:00+00:00"
        item.matched = item.identifier
        return item


def test_citation_check_endpoint_returns_audit_report(monkeypatch):
    from app.modules.citation_check import service as service_module

    monkeypatch.setattr(service_module, "CitationVerifier", _FakeVerifier)

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/citation-check",
            json={"text": "本研究参考 PMID: 39000401 与 DOI 10.1016/j.example.1。"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total"] == 2
    assert payload["summary"]["verified"] == 2
    items = {item["identifier"]: item for item in payload["items"]}
    assert items["39000401"]["verified"] is True
    assert items["39000401"]["verified_by"] == "pubmed"
    assert items["39000401"]["matched"] == "39000401"


def test_citation_check_endpoint_validates_empty_text(monkeypatch):
    from app.modules.citation_check import service as service_module

    monkeypatch.setattr(service_module, "CitationVerifier", _FakeVerifier)

    with TestClient(app) as client:
        response = client.post("/api/v1/citation-check", json={"text": ""})

    assert response.status_code == 422
