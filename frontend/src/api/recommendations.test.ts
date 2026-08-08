import { expect, test, vi } from "vitest";
import { recommendationApi } from "./recommendations";

test("posts recommendation requests to the LIVE endpoint", async () => {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ query: "肺癌", status: "completed", items: [], warnings: [] })),
  );
  vi.stubGlobal("fetch", fetchMock);

  await recommendationApi.create("肺癌", 3);

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/v1/recommendations",
    expect.objectContaining({ method: "POST", body: JSON.stringify({ query: "肺癌", candidate_count: 3 }) }),
  );
});
