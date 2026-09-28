"""Small official Zotero Web API adapter; credentials never enter persistence."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx

from app.common.exceptions import AppError


class ZoteroNotConfiguredError(AppError):
    status_code = 409
    code = "zotero_not_configured"


class ZoteroRemoteError(AppError):
    status_code = 503
    code = "zotero_remote_unavailable"


class ZoteroPermissionError(AppError):
    status_code = 403
    code = "zotero_permission_denied"


class ZoteroRateLimitedError(AppError):
    status_code = 429
    code = "zotero_rate_limited"


@dataclass(frozen=True)
class ZoteroItem:
    key: str
    version: str
    data: dict[str, object]


@dataclass(frozen=True)
class ZoteroCollectionItem:
    """One remote collection identity, including its parent relation."""

    key: str
    version: str
    name: str
    parent_key: str | None = None
    is_deleted: bool = False


@dataclass(frozen=True)
class ZoteroIncrementalResult:
    version: str | None
    items: list[ZoteroItem]
    collections: list[ZoteroCollectionItem] = field(default_factory=list)


@dataclass(frozen=True)
class ZoteroAttachment:
    """Verified bytes supplied by the official attachment endpoint."""

    filename: str
    media_type: str
    content: bytes


class ZoteroAdapter:
    """Port for Zotero's documented versioned item endpoint."""

    def __init__(self, api_key: str, library_type: str, library_id: str, *, client: httpx.AsyncClient, base_url: str = "https://api.zotero.org", max_retries: int = 3, timeout_seconds: float = 30.0) -> None:
        if not api_key: raise ZoteroNotConfiguredError("Zotero is not configured")
        self._key, self._library_type, self._library_id = api_key, library_type, library_id
        self._client, self._base_url, self._max_retries = client, base_url.rstrip("/"), max_retries
        self._timeout_seconds = timeout_seconds

    async def fetch_incremental(self, version: int | None = None) -> ZoteroIncrementalResult:
        """Read every official API page for one incremental cursor.

        Zotero exposes pagination through RFC 5988 Link headers.  Keeping this
        traversal in the adapter means repositories only ever see a complete,
        versioned result and never perform network I/O themselves.
        """
        params = {"format": "json", "limit": "100"}
        if version is not None: params["since"] = str(version)
        next_url: str | None = (
            f"{self._base_url}/{self._library_type}/{self._library_id}/items"
        )
        next_params: dict[str, str] | None = params
        items: list[ZoteroItem] = []
        observed_version: str | None = None
        while next_url is not None:
            response = await self._request("GET", next_url, params=next_params)
            observed_version = response.headers.get("Last-Modified-Version", observed_version)
            try:
                payload = response.json()
            except ValueError as exc:
                raise ZoteroRemoteError("Zotero returned invalid data") from exc
            if not isinstance(payload, list):
                raise ZoteroRemoteError("Zotero returned invalid data")
            items.extend(
                ZoteroItem(
                    key=str(item.get("key", "")),
                    version=str(item.get("version", "")),
                    data=dict(item.get("data", {})),
                )
                for item in payload
                if isinstance(item, dict) and item.get("key")
            )
            next_url = response.links.get("next", {}).get("url")
            next_params = None
        collections = await self._fetch_collections()
        return ZoteroIncrementalResult(
            version=observed_version, items=items, collections=collections
        )

    async def _fetch_collections(self) -> list[ZoteroCollectionItem]:
        next_url: str | None = (
            f"{self._base_url}/{self._library_type}/{self._library_id}/collections"
        )
        next_params: dict[str, str] | None = {"format": "json", "limit": "100"}
        collections: list[ZoteroCollectionItem] = []
        while next_url is not None:
            response = await self._request("GET", next_url, params=next_params)
            try:
                payload = response.json()
            except ValueError as exc:
                raise ZoteroRemoteError("Zotero returned invalid collection data") from exc
            if not isinstance(payload, list):
                raise ZoteroRemoteError("Zotero returned invalid collection data")
            for value in payload:
                if not isinstance(value, dict) or not value.get("key"):
                    continue
                data = value.get("data")
                if not isinstance(data, dict):
                    continue
                collections.append(
                    ZoteroCollectionItem(
                        key=str(value["key"]),
                        version=str(value.get("version", "")),
                        name=str(data.get("name") or value["key"]),
                        parent_key=str(data.get("parentCollection") or "") or None,
                        is_deleted=bool(data.get("deleted", False)),
                    )
                )
            next_url = response.links.get("next", {}).get("url")
            next_params = None
        return collections

    async def connection_test(self) -> str | None:
        """Validate the supplied key against the official endpoint without logging it."""
        response = await self._request(
            "GET", f"{self._base_url}/{self._library_type}/{self._library_id}/items/top",
            params={"limit": "1", "format": "json"},
        )
        return response.headers.get("Last-Modified-Version")

    async def fetch_attachment(self, item_key: str) -> ZoteroAttachment:
        """Download an attachment only through the official item-file endpoint."""
        response = await self._request(
            "GET",
            f"{self._base_url}/{self._library_type}/{self._library_id}/items/{item_key}/file",
        )
        filename = _content_disposition_filename(response.headers.get("Content-Disposition"))
        return ZoteroAttachment(
            filename=filename or item_key,
            media_type=response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0],
            content=response.content,
        )

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            try: response = await self._client.request(method, url, headers={"Zotero-API-Key": self._key}, timeout=self._timeout_seconds, **kwargs)
            except httpx.HTTPError as exc:
                if attempt == self._max_retries: raise ZoteroRemoteError("Zotero is temporarily unavailable") from exc
                await asyncio.sleep(0); continue
            if response.status_code == 429:
                if attempt == self._max_retries:
                    raise ZoteroRateLimitedError("Zotero rate limit exceeded")
                try:
                    retry_after = max(0.0, float(response.headers.get("Retry-After", "0")))
                except ValueError:
                    retry_after = 0.0
                await asyncio.sleep(retry_after)
                continue
            if response.status_code in {401, 403}:
                raise ZoteroPermissionError("Zotero authorization failed")
            if response.status_code >= 400: raise ZoteroRemoteError("Zotero request failed")
            return response
        raise ZoteroRemoteError("Zotero is temporarily unavailable")


def zotero_item_processing_state(data: dict[str, object]) -> str:
    """Metadata records cannot be advertised as AI-indexed documents."""
    return "attachment_pending" if data.get("itemType") == "attachment" else "metadata_only"


def _content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    for part in value.split(";"):
        key, separator, raw_value = part.strip().partition("=")
        if separator and key.casefold() == "filename":
            return raw_value.strip().strip('"')
    return None
