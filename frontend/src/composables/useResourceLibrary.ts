import { computed, reactive, readonly, shallowRef } from "vue";

import {
  DEFAULT_RESOURCE_LIBRARY_FILTERS,
  resourceLibraryApi,
  type ResourceLibraryFacets,
  type ResourceLibraryFilters,
  type ResourceLibraryItem,
} from "../api/resourceLibrary";

export const RESOURCE_LIBRARY_DEFAULT_PAGE_SIZE = 25;

/**
 * 统一管理资料库查询的可取消请求；序号校验保留为浏览器不支持取消时的第二道防线。
 */
export function useResourceLibrary() {
  const items = shallowRef<ResourceLibraryItem[]>([]);
  const filters = reactive<ResourceLibraryFilters>({ ...DEFAULT_RESOURCE_LIBRARY_FILTERS });
  const facets = shallowRef<ResourceLibraryFacets | null>(null);
  const total = shallowRef(0);
  const offset = shallowRef(0);
  const limit = shallowRef(RESOURCE_LIBRARY_DEFAULT_PAGE_SIZE);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let requestSequence = 0;
  let controller: AbortController | null = null;

  const pageNumber = computed(() => Math.floor(offset.value / limit.value) + 1);
  const hasPrevious = computed(() => offset.value > 0);
  const hasNext = computed(() => offset.value + items.value.length < total.value);

  async function loadPage(nextFilters?: Partial<ResourceLibraryFilters>, nextOffset = offset.value, nextLimit = limit.value): Promise<void> {
    Object.assign(filters, nextFilters);
    offset.value = Math.max(0, nextOffset);
    limit.value = Math.min(Math.max(1, nextLimit), 100);
    const sequence = ++requestSequence;
    controller?.abort();
    controller = new AbortController();
    loading.value = true;
    error.value = null;

    try {
      const [page, nextFacets] = await Promise.all([
        resourceLibraryApi.items(filters, offset.value, limit.value, controller.signal),
        resourceLibraryApi.facets(filters, controller.signal),
      ]);
      if (sequence !== requestSequence) return;
      items.value = page.items;
      total.value = page.total;
      facets.value = nextFacets;
    } catch (caught) {
      if (sequence !== requestSequence || (caught instanceof DOMException && caught.name === "AbortError")) return;
      error.value = caught instanceof Error ? caught.message : "资料列表暂时无法加载";
    } finally {
      if (sequence === requestSequence) loading.value = false;
    }
  }

  function cancel(): void {
    requestSequence += 1;
    controller?.abort();
    controller = null;
    loading.value = false;
  }

  return {
    items: readonly(items),
    filters: readonly(filters),
    facets: readonly(facets),
    total: readonly(total),
    offset: readonly(offset),
    limit: readonly(limit),
    loading: readonly(loading),
    error: readonly(error),
    pageNumber,
    hasPrevious,
    hasNext,
    loadPage,
    cancel,
  };
}
