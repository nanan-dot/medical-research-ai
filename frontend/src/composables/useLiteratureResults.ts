import { computed, readonly, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  literatureSearchApi,
  type ItemStateUpdate,
  type LiteratureSearchResultPage,
  type ResultFilterValues,
  type ResultQueryParams,
} from "../api/literatureSearch";

// 结果列表页大小：与后端默认 20 对齐，避免每页过大拖慢渲染。
export const DEFAULT_PAGE_SIZE = 100;

function parseQueryParam(value: string | null): string {
  return value ?? "";
}

function parseNullableBoolean(value: string | null): boolean | null {
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

// 从 URL query 还原筛选/排序参数（刷新不丢失）；非法值回退默认。
function filtersFromQuery(query: Record<string, string | string[] | null>): ResultQueryParams {
  const one = (key: string): string | null => {
    const value = query[key];
    return Array.isArray(value) ? (value[0] ?? null) : (value ?? null);
  };
  const year = one("year");
  const hasAbstract = one("has_abstract");
  const saved = one("saved");
  const readStatus = one("read_status");
  const page = Number(one("page") ?? "1");
  const sort = one("sort");
  return {
    year: year !== null && /^\d{4}$/.test(year) ? Number(year) : null,
    publication_type: parseQueryParam(one("publication_type")),
    journal: parseQueryParam(one("journal")),
    author: parseQueryParam(one("author")),
    has_abstract: parseNullableBoolean(hasAbstract),
    saved: parseNullableBoolean(saved),
    read_status: readStatus === "read" || readStatus === "unread" ? readStatus : "",
    tags: parseQueryParam(one("tags")),
    sort: sort === "newest" || sort === "classic" || sort === "custom" ? sort : "relevance",
    page: Number.isInteger(page) && page >= 1 ? page : 1,
    page_size: DEFAULT_PAGE_SIZE,
    duplicate_mode: one("duplicate_mode") === "consolidated" ? "consolidated" : "all",
  };
}

export function useLiteratureResults(resultId: number) {
  const route = useRoute();
  const router = useRouter();

  const page = shallowRef<LiteratureSearchResultPage | null>(null);
  const loading = shallowRef(false);
  const error = shallowRef<string | null>(null);
  const updating = shallowRef<Record<string, boolean>>({});

  // 筛选/排序/分页状态统一从 URL 派生：URL 是唯一数据源，刷新不丢失。
  const filters = shallowRef<ResultQueryParams>(filtersFromQuery(route.query as Record<string, string | string[] | null>));

  const filteredTotal = computed(() => page.value?.filtered_total ?? 0);
  const totalPages = computed(() => Math.max(1, Math.ceil(filteredTotal.value / DEFAULT_PAGE_SIZE)));
  const currentPage = computed(() => filters.value.page);

  async function load(): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      page.value = await literatureSearchApi.getResults(resultId, filters.value);
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "无法读取检索结果";
    } finally {
      loading.value = false;
    }
  }

  // 合并 query 而非覆盖，避免筛选/分页时抹掉 tab=results 而跳回检索中心。
  function syncUrl(): void {
    const params = filters.value;
    const query: Record<string, string> = {};
    if (params.year !== null) query.year = String(params.year);
    if (params.publication_type) query.publication_type = params.publication_type;
    if (params.journal) query.journal = params.journal;
    if (params.author) query.author = params.author;
    if (params.has_abstract !== null) query.has_abstract = String(params.has_abstract);
    if (params.saved !== null) query.saved = String(params.saved);
    if (params.read_status) query.read_status = params.read_status;
    if (params.tags) query.tags = params.tags;
    if (params.sort !== "relevance") query.sort = params.sort;
    if (params.page > 1) query.page = String(params.page);
    if (params.duplicate_mode !== "all") query.duplicate_mode = params.duplicate_mode;
    // Preserve route context such as tab=results, but remove only the keys this
    // composable owns so clearing a filter cannot leave an old URL value behind.
    const nextQuery = { ...route.query } as Record<string, string | string[] | null | undefined>;
    for (const key of ["year", "publication_type", "journal", "author", "has_abstract", "saved", "read_status", "tags", "sort", "page", "duplicate_mode"]) {
      delete nextQuery[key];
    }
    void router.replace({ query: { ...nextQuery, ...query } });
  }

  // 任何筛选字段变化：重置到第 1 页并同步 URL；加载由 route.query 变更触发。
  function applyFilters(next: ResultFilterValues): void {
    filters.value = { ...filters.value, ...next, page: 1 };
    syncUrl();
  }

  function goToPage(target: number): void {
    const clamped = Math.min(Math.max(target, 1), totalPages.value);
    if (clamped === filters.value.page) return;
    filters.value = { ...filters.value, page: clamped };
    syncUrl();
  }

  const previousPage = (): void => goToPage(filters.value.page - 1);
  const nextPage = (): void => goToPage(filters.value.page + 1);
  function setDuplicateMode(duplicateMode: "all" | "consolidated"): void {
    if (filters.value.duplicate_mode === duplicateMode) return;
    filters.value = { ...filters.value, duplicate_mode: duplicateMode, page: 1 };
    syncUrl();
  }

  // 用户态写入（saved / read_status / tags）：乐观更新当前页并回滚失败。
  async function updateState(pmid: string, request: ItemStateUpdate): Promise<void> {
    if (updating.value[pmid]) return;
    updating.value = { ...updating.value, [pmid]: true };
    const previous = page.value?.items.map((entry) => ({ pmid: entry.item.pmid, state: entry.state }));
    try {
      const updated = await literatureSearchApi.updateItemState(resultId, pmid, request);
      if (page.value) {
        page.value = {
          ...page.value,
          items: page.value.items.map((entry) => (entry.item.pmid === pmid ? { ...entry, state: updated } : entry)),
        };
      }
    } catch (caught) {
      error.value = caught instanceof Error ? caught.message : "无法更新结果状态";
      // 写入失败回滚到写入前状态，避免前端与后端状态不一致。
      if (page.value && previous) {
        page.value = {
          ...page.value,
          items: page.value.items.map((entry) => {
            const before = previous.find((item) => item.pmid === entry.item.pmid)?.state;
            return before === undefined ? entry : { ...entry, state: before };
          }),
        };
      }
    } finally {
      updating.value = { ...updating.value, [pmid]: false };
    }
  }

  // 路由变化（后退/前进或手动改 URL）时，从 URL 重新派生筛选并加载；
  // immediate 让首次进入即按当前 URL 加载。
  watch(
    () => route.query,
    () => {
      filters.value = filtersFromQuery(route.query as Record<string, string | string[] | null>);
      void load();
    },
    { immediate: true },
  );

  return {
    // 注意：不用 Vue readonly() 深度包装 page——它会把 items 里的数组递归变成
    // readonly，与 RankedCitationItem.authors: string[] 类型冲突。page 的 ref
    // 本身不对外暴露 setter（只读用法），类型上保持可变数组即可。
    page,
    filters: readonly(filters),
    loading: readonly(loading),
    error: readonly(error),
    updating: readonly(updating),
    filteredTotal: readonly(filteredTotal),
    totalPages,
    currentPage,
    hasPrevious: computed(() => filters.value.page > 1),
    hasNext: computed(() => filters.value.page < totalPages.value),
    applyFilters,
    goToPage,
    previousPage,
    nextPage,
    setDuplicateMode,
    updateState,
    // 去重决策/扫描等外部副作用完成后，强制用当前 filters 重新请求结果，
    // 不依赖 URL 变化（决策不改变 duplicate_mode，故不能靠 watch(route.query) 触发）。
    reload: load,
  };
}
