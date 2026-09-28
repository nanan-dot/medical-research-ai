import { effectScope, shallowRef } from "vue";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { searchStrategiesApi } from "../api/searchStrategies";
import type { SearchStrategyDraft } from "../types/searchStrategy";
import { useStrategyAutosave } from "./useStrategyAutosave";

vi.mock("../api/searchStrategies", () => ({
  searchStrategiesApi: { patch: vi.fn() },
}));

const draft: SearchStrategyDraft = {
  id: 12,
  research_question: "肺间质病常见临床表现",
  intent_mode: "unstructured",
  intent: {},
  limits: {},
  query_text: "old query",
  query_source: "generated",
  fingerprint: "original",
  revision: 3,
  generation_state: "ready",
  validation_state: "stale",
  count_state: "stale",
  count: {},
  last_saved_at: "2026-08-23T00:00:00Z",
  terms: [],
  mesh_terms: [],
};

afterEach(() => {
  vi.clearAllMocks();
  vi.useRealTimers();
});

describe("useStrategyAutosave", () => {
  it("debounces rapid query edits and saves only the latest query", async () => {
    vi.useFakeTimers();
    vi.mocked(searchStrategiesApi.patch).mockResolvedValue({
      ...draft,
      query_text: "latest query",
      revision: 4,
    });
    const scope = effectScope();
    const strategy = shallowRef<SearchStrategyDraft | null>(draft);
    const autosave = scope.run(() => useStrategyAutosave(strategy));

    autosave?.schedule("first query");
    autosave?.schedule("latest query");
    await vi.advanceTimersByTimeAsync(700);

    expect(searchStrategiesApi.patch).toHaveBeenCalledTimes(1);
    expect(searchStrategiesApi.patch).toHaveBeenCalledWith(12, {
      revision: 3,
      query_text: "latest query",
      query_source: "user_edited",
    });
    expect(strategy.value?.revision).toBe(4);
    expect(autosave?.saveState.value).toBe("saved");
    scope.stop();
  });

  it("marks revision conflicts distinctly and keeps the last authoritative draft", async () => {
    vi.mocked(searchStrategiesApi.patch).mockRejectedValue(new ApiError("策略已被其他窗口更新", 409));
    const scope = effectScope();
    const strategy = shallowRef<SearchStrategyDraft | null>(draft);
    const autosave = scope.run(() => useStrategyAutosave(strategy));

    await autosave?.saveNow("edited query");

    expect(autosave?.saveState.value).toBe("conflict");
    expect(autosave?.error.value).toBe("策略已被其他窗口更新");
    expect(strategy.value).toEqual(draft);
    scope.stop();
  });
});
