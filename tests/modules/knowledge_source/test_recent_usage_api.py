"""行为测试：来源最近使用记录和稳定排序。"""

from pathlib import Path

from fastapi.testclient import TestClient

from tests.modules.knowledge_source.test_api import create_source


def test_opened_endpoint_persists_access_and_recent_sort_is_stable(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-RECENT-01/03/04：显式打开才更新时间，NULL 最后且分页无重复。"""
    source_ids: list[int] = []
    for index in range(3):
        root = tmp_path / f"source-{index}"
        root.mkdir()
        source_ids.append(create_source(client, root).json()["id"])

    opened = client.post(f"/api/v1/knowledge-sources/{source_ids[1]}/opened")
    assert opened.status_code == 204

    first_page = client.get(
        "/api/v1/knowledge-sources/page",
        params={"sort_by": "last_opened", "limit": 2},
    ).json()["items"]
    second_page = client.get(
        "/api/v1/knowledge-sources/page",
        params={"sort_by": "last_opened", "offset": 2, "limit": 2},
    ).json()["items"]

    assert first_page[0]["id"] == source_ids[1]
    assert first_page[0]["last_opened_at"] is not None
    assert [item["id"] for item in first_page + second_page] == [
        source_ids[1],
        source_ids[0],
        source_ids[2],
    ]


def test_read_only_endpoints_do_not_record_recent_usage(
    client: TestClient, tmp_path: Path
) -> None:
    """AC-RECENT-02：列表、汇总与状态查询不得污染访问时间。"""
    root = tmp_path / "source"
    root.mkdir()
    source_id = create_source(client, root).json()["id"]

    assert client.get("/api/v1/knowledge-sources").status_code == 200
    assert client.get("/api/v1/knowledge-sources/page").status_code == 200
    assert client.get("/api/v1/knowledge-sources/summary").status_code == 200
    assert client.get(f"/api/v1/knowledge-sources/{source_id}/sync-status").status_code == 200

    source = client.get(f"/api/v1/knowledge-sources/{source_id}").json()
    assert source["last_opened_at"] is None
