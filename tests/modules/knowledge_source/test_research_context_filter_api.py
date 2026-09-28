"""行为测试：知识来源关联真实研究项目并在 SQL 分页前筛选。"""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.modules.knowledge_source.test_api import create_source


def test_source_research_context_association_and_filter(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-RESEARCH-01/02/03/05：关联幂等、搜索去重，解除不删除实体。"""
    context = client.post("/api/v1/research-contexts", json={"name": "ILD Study"})
    assert context.status_code == 201
    context_id = context.json()["id"]
    source_ids: list[int] = []
    for name in ("a", "b"):
        root = tmp_path / name
        root.mkdir()
        source_ids.append(create_source(client, root).json()["id"])

    assert (
        client.put(
            f"/api/v1/knowledge-sources/{source_ids[0]}/research-contexts/{context_id}"
        ).status_code
        == 204
    )
    assert (
        client.put(
            f"/api/v1/knowledge-sources/{source_ids[0]}/research-contexts/{context_id}"
        ).status_code
        == 204
    )

    filtered = client.get(
        "/api/v1/knowledge-sources/page",
        params={"research_context_id": context_id},
    ).json()
    searched = client.get(
        "/api/v1/knowledge-sources/page", params={"q": "ild study"}
    ).json()
    assert filtered["total"] == 1
    assert searched["total"] == 1
    assert filtered["items"][0]["research_context_count"] == 1

    assert (
        client.delete(
            f"/api/v1/knowledge-sources/{source_ids[0]}/research-contexts/{context_id}"
        ).status_code
        == 204
    )
    assert client.get(f"/api/v1/research-contexts/{context_id}").status_code == 200
    assert client.get(f"/api/v1/knowledge-sources/{source_ids[0]}").status_code == 200
