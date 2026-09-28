"""Contract tests for the official Zotero adapter; all network I/O is mocked."""

from __future__ import annotations

import asyncio

import httpx

from app.core.config import settings


def test_zotero_not_configured_is_structured(library_client, monkeypatch) -> None:
    """AC-LIB-10: missing credentials degrade locally without fake sources or counts."""
    client, seed, _ = library_client
    seed(relative_path="still-local.md")
    monkeypatch.setattr(settings, "ZOTERO_API_KEY", "")

    response = client.post("/api/v1/knowledge-sources/zotero/connection-test")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "zotero_not_configured"
    assert client.get("/api/v1/library/summary").json()["total"] == 1


def test_zotero_incremental_sync_with_retry() -> None:
    """AC-LIB-11: the official adapter honors Retry-After and returns a version cursor."""
    from app.modules.library.zotero import ZoteroAdapter

    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        assert request.headers["Zotero-API-Key"] == "test-key"
        if request.url.path.endswith("/collections"):
            return httpx.Response(200, json=[])
        if requests == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            headers={"Last-Modified-Version": "17"},
            json=[
                {
                    "key": "ITEM01",
                    "version": 17,
                    "data": {"itemType": "attachment", "title": "Attachment", "parentItem": "PARENT"},
                }
            ],
        )

    async def fetch() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = ZoteroAdapter(
                api_key="test-key",
                library_type="users",
                library_id="42",
                client=client,
                max_retries=1,
            )
            result = await adapter.fetch_incremental(version=16)
            assert result.version == "17"
            assert result.items[0].key == "ITEM01"

    asyncio.run(fetch())
    assert requests == 3


def test_zotero_attachment_download_uses_the_official_file_endpoint() -> None:
    """AC-LIB-11: attachment bytes stay behind the adapter boundary."""
    from app.modules.library.zotero import ZoteroAdapter

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/items/FILE01/file")
        assert request.headers["Zotero-API-Key"] == "test-key"
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": 'attachment; filename="official.pdf"',
            },
            content=b"%PDF-1.4\nofficial attachment",
        )

    async def fetch() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            attachment = await ZoteroAdapter(
                api_key="test-key",
                library_type="users",
                library_id="42",
                client=client,
            ).fetch_attachment("FILE01")
        assert attachment.filename == "official.pdf"
        assert attachment.media_type == "application/pdf"
        assert attachment.content.startswith(b"%PDF-")

    asyncio.run(fetch())


def test_zotero_metadata_only_is_not_ai_available() -> None:
    """AC-LIB-12: records without usable attachments remain metadata_only."""
    from app.modules.library.zotero import zotero_item_processing_state

    assert zotero_item_processing_state({"itemType": "journalArticle", "title": "Metadata"}) == "metadata_only"


def test_zotero_source_crud_and_metadata_sync_are_persistent(library_client, monkeypatch) -> None:
    """AC-LIB-10/11/12: a mocked incremental sync persists metadata and its cursor."""
    client, _, _ = library_client
    monkeypatch.setattr(settings, "ZOTERO_API_KEY", "test-key")
    created = client.post(
        "/api/v1/knowledge-sources/zotero",
        json={"name": "My Zotero", "library_type": "users", "library_id": "42"},
    )
    assert created.status_code == 201
    source_id = created.json()["knowledge_source_id"]

    from app.core.database import get_session
    from app.modules.library.zotero import (
        ZoteroAttachment,
        ZoteroCollectionItem,
        ZoteroIncrementalResult,
        ZoteroItem,
    )
    from app.modules.library.zotero_service import ZoteroSyncService

    async def run_sync() -> None:
        override = client.app.dependency_overrides[get_session]
        async for session in override():
            service = ZoteroSyncService(session)
            result = await service.sync(
                source_id,
                lambda: ZoteroIncrementalResult(
                    version="22",
                    items=[
                        ZoteroItem(
                            key="META1",
                            version="22",
                            data={"itemType": "journalArticle", "title": "Only metadata"},
                        ),
                        ZoteroItem(
                            key="ATTACH1",
                            version="22",
                            data={"itemType": "attachment", "title": "Queued attachment"},
                        ),
                    ],
                collections=[
                    ZoteroCollectionItem(
                        key="ROOT", version="22", name="Root collection"
                    ),
                    ZoteroCollectionItem(
                        key="CHILD",
                        version="22",
                        name="Child collection",
                        parent_key="ROOT",
                    ),
                ],
                ),
                lambda _: ZoteroAttachment(
                    filename="queued.pdf",
                    media_type="application/pdf",
                    content=b"%PDF-1.4\nmock attachment",
                ),
            )
            assert result["metadata_only"] == 1

    asyncio.run(run_sync())
    items = client.get("/api/v1/library/items", params={"source_id": source_id})
    assert items.status_code == 200
    rows = {item["display_name"]: item for item in items.json()["items"]}
    assert rows["META1"]["status"] == "metadata_only"
    assert rows["queued.pdf"]["task_status"] == "queued"
    assert rows["queued.pdf"]["file_size"] > 0
    tree = client.get("/api/v1/library/source-tree").json()
    zotero = next(group for group in tree["groups"] if group["source_type"] == "zotero")
    source = next(node for node in zotero["children"] if node["source_id"] == source_id)
    root = next(node for node in source["children"] if node["name"] == "Root collection")
    assert root["children"][0]["name"] == "Child collection"
    assert client.delete(f"/api/v1/knowledge-sources/zotero/{source_id}").status_code == 204


def test_zotero_sync_submission_is_durable_and_idempotent(library_client) -> None:
    """AC-LIB-15: a page refresh reuses the same active Zotero sync task."""
    client, _, _ = library_client
    source = client.post(
        "/api/v1/knowledge-sources/zotero",
        json={"name": "Task library", "library_type": "groups", "library_id": "77"},
    )
    source_id = source.json()["knowledge_source_id"]

    first = client.post(f"/api/v1/knowledge-sources/{source_id}/sync")
    second = client.post(f"/api/v1/knowledge-sources/{source_id}/sync")

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["task_id"] == second.json()["task_id"]
    assert first.json()["status"] == "queued"


def test_zotero_tombstone_keeps_a_non_ai_auditable_record(library_client) -> None:
    """AC-LIB-11/12: remote deletion never leaves a prior index usable."""
    client, _, _ = library_client
    created = client.post(
        "/api/v1/knowledge-sources/zotero",
        json={"name": "Tombstone", "library_type": "users", "library_id": "99"},
    )
    source_id = created.json()["knowledge_source_id"]

    from app.core.database import get_session
    from app.modules.library.zotero import ZoteroIncrementalResult, ZoteroItem
    from app.modules.library.zotero_service import ZoteroSyncService

    async def sync_deleted_item() -> None:
        override = client.app.dependency_overrides[get_session]
        async for session in override():
            service = ZoteroSyncService(session)
            await service.sync(
                source_id,
                lambda: ZoteroIncrementalResult(
                    version="1",
                    items=[
                        ZoteroItem(
                            key="DELETED",
                            version="1",
                            data={"itemType": "journalArticle", "title": "Will delete"},
                        )
                    ],
                ),
            )
            await service.sync(
                source_id,
                lambda: ZoteroIncrementalResult(
                    version="2",
                    items=[
                        ZoteroItem(
                            key="DELETED",
                            version="2",
                            data={"deleted": True},
                        )
                    ],
                ),
            )

    asyncio.run(sync_deleted_item())
    item = client.get("/api/v1/library/items", params={"source_id": source_id}).json()["items"][0]
    assert item["status"] == "needs_attention"
    assert item["error_code"] == "zotero_tombstoned"
    assert item["paperqa_index_key"] is None
