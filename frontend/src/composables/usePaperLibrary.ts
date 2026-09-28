import { computed, reactive, readonly, shallowRef } from "vue";

import {
  DEFAULT_PAPER_FILTERS,
  paperLibraryApi,
  type PaperFacets,
  type PaperFilters,
  type PaperItem,
  type PaperSummary,
} from "../api/paperLibrary";

export const PAPER_LIBRARY_PAGE_SIZE = 5;

function cloneFilters(filters: Readonly<PaperFilters>): PaperFilters {
  return {
    ...filters,
    readingStatus: [...filters.readingStatus],
    analysisStatus: [...filters.analysisStatus],
    paperTypes: [...filters.paperTypes],
    researchRoles: [...filters.researchRoles],
    researchIds: [...filters.researchIds],
    tags: [...filters.tags],
  };
}

/** 保留最近一次成功列表，刷新时显示陈旧数据并取消过期请求。 */
export function usePaperLibrary() {
  const filters = reactive<PaperFilters>(cloneFilters(DEFAULT_PAPER_FILTERS));
  const items = shallowRef<PaperItem[]>([]);
  const facets = shallowRef<PaperFacets | null>(null);
  const summary = shallowRef<PaperSummary | null>(null);
  const total = shallowRef(0);
  const offset = shallowRef(0);
  const loading = shallowRef(false);
  const initialized = shallowRef(false);
  const error = shallowRef<string | null>(null);
  let controller: AbortController | null = null;
  let sequence = 0;

  const hasPrevious = computed(() => offset.value > 0);
  const hasNext = computed(() => offset.value + items.value.length < total.value);
  const page = computed(() => Math.floor(offset.value / PAPER_LIBRARY_PAGE_SIZE) + 1);
  const pageCount = computed(() => Math.max(1, Math.ceil(total.value / PAPER_LIBRARY_PAGE_SIZE)));
  const isRefreshing = computed(() => initialized.value && loading.value);

  async function load(next?: Partial<PaperFilters>, nextOffset = offset.value): Promise<void> {
    if (next) Object.assign(filters, next);
    offset.value = Math.max(0, nextOffset);
    const requestId = ++sequence;
    controller?.abort();
    controller = new AbortController();
    loading.value = true;
    error.value = null;
    try {
      const [nextPage, nextSummary, nextFacets] = await Promise.all([
        paperLibraryApi.items(filters, offset.value, PAPER_LIBRARY_PAGE_SIZE, controller.signal),
        paperLibraryApi.summary(controller.signal),
        paperLibraryApi.facets(filters, controller.signal),
      ]);
      if (requestId !== sequence) return;
      items.value = [...nextPage.items];
      total.value = nextPage.total;
      summary.value = nextSummary;
      facets.value = nextFacets;
      initialized.value = true;
    } catch (cause) {
      if (requestId !== sequence || (cause instanceof DOMException && cause.name === "AbortError")) return;
      error.value = cause instanceof Error ? cause.message : "论文库暂时无法加载";
    } finally {
      if (requestId === sequence) loading.value = false;
    }
  }

  function reset(): Promise<void> {
    return load(cloneFilters(DEFAULT_PAPER_FILTERS), 0);
  }

  function cancel(): void { sequence += 1; controller?.abort(); }

  return {
    filters: readonly(filters), items: readonly(items), facets: readonly(facets), summary: readonly(summary),
    total: readonly(total), offset: readonly(offset), loading: readonly(loading), initialized: readonly(initialized),
    error: readonly(error), page, pageCount, hasPrevious, hasNext, isRefreshing,
    load, reset, cancel, pageSize: PAPER_LIBRARY_PAGE_SIZE,
  };
}
