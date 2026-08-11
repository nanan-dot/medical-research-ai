import { computed, getCurrentInstance, onUnmounted, shallowRef } from "vue";
import { documentNavigationApi, type DocumentNavigationResponse } from "../api/documentNavigation";

export function useDocumentNavigation() {
  const result = shallowRef<DocumentNavigationResponse | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let controller: AbortController | null = null;
  let requestId = 0;
  let lastRequest: [string, number | null, boolean] | null = null;
  const hasSearched = computed(() => result.value !== null || error.value !== null);

  async function search(query: string, knowledgeSourceId: number | null, indexedOnly: boolean): Promise<void> {
    lastRequest = [query, knowledgeSourceId, indexedOnly];
    controller?.abort();
    controller = new AbortController();
    const currentRequestId = ++requestId;
    loading.value = true;
    error.value = null;
    try {
      const response = await documentNavigationApi.search({ query, knowledge_source_id: knowledgeSourceId ?? undefined, indexed_only: indexedOnly }, controller.signal);
      // 用户连续提交时，旧响应即使较晚返回也不能覆盖最新检索条件。
      if (currentRequestId === requestId) result.value = response;
    } catch (caught) {
      if (currentRequestId === requestId && !(caught instanceof DOMException && caught.name === "AbortError")) {
        result.value = null;
        error.value = caught instanceof Error ? caught.message : "资料导航请求失败";
      }
    } finally {
      if (currentRequestId === requestId) loading.value = false;
    }
  }

  function retry(): Promise<void> { return lastRequest ? search(...lastRequest) : Promise.resolve(); }
  // 组件卸载时释放请求；实例外单元测试仍可复用同一纯状态逻辑。
  if (getCurrentInstance()) onUnmounted(() => controller?.abort());
  return { result, loading, error, hasSearched, search, retry };
}
