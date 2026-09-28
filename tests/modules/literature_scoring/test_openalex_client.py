"""OpenAlex batching keeps citation enrichment reliable and truth-preserving."""

import httpx
import pytest

from app.modules.literature_scoring.openalex_client import OpenAlexClient


@pytest.mark.asyncio
async def test_batch_lookup_maps_metrics_and_marks_only_missing_pmids_not_found() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "ids": {"pmid": "https://pubmed.ncbi.nlm.nih.gov/123/"},
                        "cited_by_count": 17,
                        "counts_by_year": [{"year": 2025, "cited_by_count": 4}],
                    }
                ]
            },
        )

    client = OpenAlexClient(transport=httpx.MockTransport(handler))
    metrics = await client.metrics_for_pmids(["123", "456"])

    assert len(requests) == 1
    assert requests[0].url.params["filter"] == "pmid:123|456"
    assert metrics[0].cited_by_count == 17
    assert metrics[0].counts_by_year == {2025: 4}
    assert metrics[0].status == "available"
    assert metrics[1].status == "not_found"


@pytest.mark.asyncio
async def test_batch_lookup_retries_transient_provider_failure() -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"results": []})

    client = OpenAlexClient(transport=httpx.MockTransport(handler))
    metrics = await client.metrics_for_pmids(["123"])

    assert calls == 2
    assert metrics[0].status == "not_found"
