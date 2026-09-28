import { onScopeDispose, shallowRef, type Ref } from "vue";
import { ApiError } from "../api/client";
import { searchStrategiesApi } from "../api/searchStrategies";
import type { SearchStrategyDraft, StrategySaveState } from "../types/searchStrategy";

const AUTOSAVE_DELAY_MS = 700;

/** Debounces draft updates and preserves local edits when the server rejects a save. */
export function useStrategyAutosave(strategy: Ref<SearchStrategyDraft | null>) {
  const saveState = shallowRef<StrategySaveState>("unsaved");
  const error = shallowRef<string | null>(null);
  let timer: ReturnType<typeof setTimeout> | null = null;
  let latestQuery = "";

  async function save(queryText = latestQuery): Promise<void> {
    const current = strategy.value;
    if (current === null) return;
    latestQuery = queryText;
    saveState.value = "saving";
    error.value = null;
    try {
      strategy.value = await searchStrategiesApi.patch(current.id, {
        revision: current.revision,
        query_text: latestQuery,
        query_source: "user_edited",
      });
      saveState.value = "saved";
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "保存策略失败。";
      error.value = message;
      saveState.value = caught instanceof ApiError && caught.status === 409 ? "conflict" : "failed";
    }
  }

  function schedule(queryText: string): void {
    latestQuery = queryText;
    saveState.value = "unsaved";
    if (timer !== null) clearTimeout(timer);
    timer = setTimeout(() => {
      timer = null;
      void save();
    }, AUTOSAVE_DELAY_MS);
  }

  function retry(): void {
    if (latestQuery) void save(latestQuery);
  }

  onScopeDispose(() => {
    if (timer !== null) clearTimeout(timer);
  });

  return { saveState, error, schedule, retry, saveNow: save };
}
