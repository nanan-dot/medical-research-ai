"""Small client for the official NLM MeSH lookup service."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import httpx

MeshFetcher = Callable[[str], Awaitable[list[dict[str, Any]]]]


class MeshClient:
    """Fetch only source-labelled MeSH candidates; no inferred descriptors."""

    base_url = "https://id.nlm.nih.gov/mesh/lookup/descriptor"
    request_timeout = httpx.Timeout(8.0, connect=3.0)

    def __init__(self, fetcher: MeshFetcher | None = None) -> None:
        self._fetcher = fetcher or self._fetch

    async def lookup(self, term: str) -> list[dict[str, str]]:
        if not term.isascii() or not term.strip():
            return []
        rows = await self._fetcher(term)
        return [
            {
                "descriptor": str(row["label"]),
                "mesh_id": str(row["resource"]).rsplit("/", 1)[-1],
                "source": "NLM MeSH",
            }
            for row in rows
            if isinstance(row.get("label"), str)
            and isinstance(row.get("resource"), str)
        ]

    async def _fetch(self, term: str) -> list[dict[str, Any]]:
        # 本地应用经常携带开发代理；NLM 的 TLS 握手若被失效代理截获会超时。
        # 因此先直连官方服务，再只对网络层失败回退环境代理，避免把可验证的
        # 描述符写成 unavailable，同时仍兼容必须经企业代理出网的部署。
        try:
            payload = await self._request(term, trust_env=False)
        except httpx.TransportError:
            payload = await self._request(term, trust_env=True)
        return payload if isinstance(payload, list) else []

    async def _request(self, term: str, *, trust_env: bool) -> Any:
        async with httpx.AsyncClient(
            timeout=self.request_timeout,
            trust_env=trust_env,
        ) as client:
            response = await client.get(
                self.base_url,
                params={"label": term, "match": "exact", "limit": 5},
            )
            response.raise_for_status()
            return response.json()
