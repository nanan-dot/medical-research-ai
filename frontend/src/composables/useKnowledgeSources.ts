import { computed, readonly, ref, shallowRef } from "vue";
import { knowledgeSourcesApi, type KnowledgeBaseSummary, type KnowledgeSource, type KnowledgeSourceQuery } from "../api/knowledgeSources";

export const KNOWLEDGE_SOURCE_SEARCH_DEBOUNCE_MS = 350;

export function useKnowledgeSources() {
  const items = ref<KnowledgeSource[]>([]); const summary = shallowRef<KnowledgeBaseSummary | null>(null); const total = shallowRef(0); const isLoading = shallowRef(false); const error = shallowRef<string | null>(null); let latestRequestId = 0;
  const hasSources = computed(() => total.value > 0);
  async function load(query?: KnowledgeSourceQuery | Event): Promise<void> {
    const requestId = ++latestRequestId; isLoading.value = true; error.value = null;
    try { if (!query || !("sortBy" in query)) { items.value = await knowledgeSourcesApi.list(); total.value = items.value.length; return; } const [page, nextSummary] = await Promise.all([knowledgeSourcesApi.page(query), knowledgeSourcesApi.summary()]); if (requestId !== latestRequestId) return; items.value = page.items; total.value = page.total; summary.value = nextSummary; }
    catch (caught) { if (requestId === latestRequestId) error.value = caught instanceof Error ? caught.message : "无法读取知识库"; }
    finally { if (requestId === latestRequestId) isLoading.value = false; }
  }
  function replaceItem(next: KnowledgeSource): void { items.value = items.value.map((item) => item.id === next.id ? next : item); }
  return { items: readonly(items), sources: readonly(items), summary: readonly(summary), total: readonly(total), isLoading: readonly(isLoading), loading: readonly(isLoading), error: readonly(error), hasSources, load, replaceItem };
}
