import { expect, test, vi } from "vitest";
import { recommendationApi } from "./recommendations";

test("maps every Recommendation V5 operation to the result-scoped contract", async () => {
  const fetchMock = vi.fn().mockImplementation(() => Promise.resolve(new Response(JSON.stringify({}))));
  vi.stubGlobal("fetch", fetchMock);
  await recommendationApi.createRun(42, { intent_snapshot_id: 7, mode: "balanced", candidate_count: 10 });
  await recommendationApi.getStatus(42); await recommendationApi.getActive(42, { page: 2, page_size: 5, sort: "created", overlap: "covered" });
  await recommendationApi.listRuns(42); await recommendationApi.getRun(42, 9); await recommendationApi.getExplanation(42, 9, "123/unsafe");
  await recommendationApi.accept(42, 9, "123"); await recommendationApi.dismiss(42, 9, "123", "off_topic"); await recommendationApi.cancel(42);
  expect(fetchMock.mock.calls.map(call => [call[0], (call[1] as RequestInit | undefined)?.method ?? "GET"])).toEqual([
    ["/api/v1/literature-search/42/recommendations/runs", "POST"], ["/api/v1/literature-search/42/recommendations/status", "GET"],
    ["/api/v1/literature-search/42/recommendations/active?page=2&page_size=5&sort=created&overlap=covered", "GET"], ["/api/v1/literature-search/42/recommendations/runs", "GET"],
    ["/api/v1/literature-search/42/recommendations/runs/9", "GET"], ["/api/v1/literature-search/42/recommendations/runs/9/items/123%2Funsafe/explanation", "GET"],
    ["/api/v1/literature-search/42/recommendations/runs/9/items/123/accept", "POST"], ["/api/v1/literature-search/42/recommendations/runs/9/items/123/dismiss", "POST"],
    ["/api/v1/literature-search/42/recommendations/cancel", "POST"],
  ]);
  expect((fetchMock.mock.calls[0][1] as RequestInit).body).toBe(JSON.stringify({ intent_snapshot_id: 7, mode: "balanced", candidate_count: 10 }));
  expect((fetchMock.mock.calls[7][1] as RequestInit).body).toBe(JSON.stringify({ reason: "off_topic" }));
});
