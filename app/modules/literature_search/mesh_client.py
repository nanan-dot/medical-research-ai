"""Small client for the official NLM MeSH lookup service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

MeshFetcher = Callable[[str], Awaitable[list[dict[str, Any]]]]


class MeshClient:
    """Fetch only source-labelled MeSH candidates; no inferred descriptors."""

    base_url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"

    def __init__(self, fetcher: MeshFetcher | None = None) -> None:
        self._fetcher = fetcher or self._fetch

    async def lookup(self, term: str) -> list[dict[str, str]]:
        if not term.isascii() or not term.strip():
            return []
        rows = await self._fetcher(term)
        return [
            {"descriptor": str(row["label"]), "mesh_id": str(row["resource"]).rsplit("/", 1)[-1], "source": "NLM MeSH"}
            for row in rows
            if isinstance(row.get("label"), str) and isinstance(row.get("resource"), str)
        ]

    async def _fetch(self, term: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(self.base_url, params={"label": term, "match": "exact", "limit": 5})
            response.raise_for_status()
            payload: Any = response.json()
        return payload if isinstance(payload, list) else []
