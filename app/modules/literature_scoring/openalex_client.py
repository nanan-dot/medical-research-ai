"""Rate-safe OpenAlex work lookup used while building score generations."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class OpenAlexMetrics:
    cited_by_count: int | None
    counts_by_year: dict[int, int]
    status: str
    reason: str | None = None


class OpenAlexClient:
    """Fetch OpenAlex metrics in bounded batches instead of one request per paper."""

    base_url = "https://api.openalex.org/works"
    batch_size = 50
    max_concurrency = 3
    max_attempts = 3

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def metrics_for_pmid(self, pmid: str) -> OpenAlexMetrics:
        """Compatibility lookup for flows that request one PMID."""
        results = await self.metrics_for_pmids([pmid])
        return results[0]

    async def metrics_for_pmids(self, pmids: Sequence[str]) -> list[OpenAlexMetrics]:
        """Return metrics in input order using OR-filter batches and bounded retries."""
        if not pmids:
            return []
        chunks = [
            list(pmids[index : index + self.batch_size])
            for index in range(0, len(pmids), self.batch_size)
        ]
        semaphore = asyncio.Semaphore(self.max_concurrency)
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            transport=self._transport,
            headers={"User-Agent": "rag-medicine/1.0 (OpenAlex citation enrichment)"},
        ) as client:
            batches = await asyncio.gather(
                *(self._metrics_for_batch(client, semaphore, chunk) for chunk in chunks)
            )
        by_pmid = {pmid: metric for batch in batches for pmid, metric in batch.items()}
        return [
            by_pmid.get(
                pmid,
                OpenAlexMetrics(None, {}, "not_found", "openalex_work_not_found"),
            )
            for pmid in pmids
        ]

    async def _metrics_for_batch(
        self,
        client: httpx.AsyncClient,
        semaphore: asyncio.Semaphore,
        pmids: list[str],
    ) -> dict[str, OpenAlexMetrics]:
        async with semaphore:
            payload = await self._request_batch(client, pmids)
        if payload is None:
            return {
                pmid: OpenAlexMetrics(None, {}, "unavailable", "openalex_unavailable")
                for pmid in pmids
            }
        output: dict[str, OpenAlexMetrics] = {}
        for work in payload.get("results", []):
            if not isinstance(work, dict):
                continue
            pmid = self._pmid_from_work(work)
            if pmid:
                output[pmid] = self._from_work(work)
        for pmid in pmids:
            output.setdefault(
                pmid,
                OpenAlexMetrics(None, {}, "not_found", "openalex_work_not_found"),
            )
        return output

    async def _request_batch(
        self, client: httpx.AsyncClient, pmids: list[str]
    ) -> dict[str, Any] | None:
        params = {
            "filter": f"pmid:{'|'.join(pmids)}",
            "per-page": str(len(pmids)),
            "select": "id,ids,cited_by_count,counts_by_year",
        }
        for attempt in range(self.max_attempts):
            try:
                response = await client.get(self.base_url, params=params)
                if response.status_code == 200:
                    payload = response.json()
                    return payload if isinstance(payload, dict) else None
                if response.status_code != 429 and response.status_code < 500:
                    return None
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
            except (httpx.HTTPError, ValueError):
                delay = 0.5 * (2**attempt)
            if attempt + 1 < self.max_attempts:
                await asyncio.sleep(min(delay, 5.0))
        return None

    @staticmethod
    def _pmid_from_work(work: dict[str, Any]) -> str | None:
        ids = work.get("ids")
        if not isinstance(ids, dict):
            return None
        value = ids.get("pmid")
        if not isinstance(value, str) or not value:
            return None
        return value.rstrip("/").rsplit("/", 1)[-1]

    @staticmethod
    def _from_work(work: dict[str, Any]) -> OpenAlexMetrics:
        counts = {
            int(entry["year"]): int(entry["cited_by_count"])
            for entry in work.get("counts_by_year", [])
            if isinstance(entry, dict)
            and entry.get("year") is not None
            and entry.get("cited_by_count") is not None
        }
        cited = work.get("cited_by_count")
        return OpenAlexMetrics(
            int(cited) if isinstance(cited, int) else None,
            counts,
            "available" if isinstance(cited, int) else "unavailable",
            None if isinstance(cited, int) else "openalex_citation_count_missing",
        )
