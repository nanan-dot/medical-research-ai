import { computed, onMounted, reactive, shallowRef, watch } from "vue";
import {
  literatureStrategiesApi,
  type StrategyDetail,
  type StrategyListItem,
} from "../api/literatureStrategies";
import { ApiError } from "../api/client";
import { researchContextsApi, type ResearchContext } from "../api/researchContexts";

const PAGE_SIZE = 10;

export function useLiteratureHistory() {
  const items = shallowRef<StrategyListItem[]>([]);
  const selected = shallowRef<StrategyDetail | null>(null);
  const total = shallowRef(0);
  const projects = shallowRef<ResearchContext[]>([]);
  const offset = shallowRef(0);
  const loading = shallowRef(false);
  const detailLoading = shallowRef(false);
  const rerunning = shallowRef(false);
  const error = shallowRef("");
  const filters = reactive({
    query: "",
    researchContextId: "",
    framework: "",
    timeRange: "",
    sort: "updated_at",
    quickFilter: "all" as "all" | "changes" | "failed",
    archived: false,
  });
  let latestLoadId = 0;
  const currentPage = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1);
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
  const projectIds = computed(() =>
    [...new Set(items.value.map((item) => item.research_context_id).filter(Boolean))] as number[],
  );

  async function select(id: number) {
    detailLoading.value = true;
    try {
      selected.value = await literatureStrategiesApi.get(id);
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : "无法读取策略详情";
    } finally {
      detailLoading.value = false;
    }
  }

  function clearSelection() {
    selected.value = null;
  }

  function escapeCsv(value: unknown) {
    return `"${String(value ?? "").replaceAll('"', '""')}"`;
  }

  function downloadCsv(rows: unknown[][], filename: string) {
    // UTF-8 BOM ensures Excel on Windows opens Chinese column names without mojibake.
    const content = `\uFEFF${rows.map((row) => row.map(escapeCsv).join(",")).join("\r\n")}`;
    const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function latestExecution(strategy: StrategyDetail) {
    return [...strategy.executions].sort((a, b) =>
      b.created_at.localeCompare(a.created_at),
    )[0];
  }

  function strategyExportRow(strategy: StrategyDetail) {
    const version = strategy.current_version;
    const execution = latestExecution(strategy);
    return [
      strategy.name,
      version.original_query,
      strategy.framework,
      strategy.database,
      `v${version.version}`,
      version.term_groups.join("；"),
      version.mesh_terms.join("；"),
      version.start_year && version.end_year
        ? `${version.start_year}–${version.end_year}`
        : "",
      version.search_string,
      version.filters,
      execution?.status ?? "未执行",
      execution?.result_count ?? 0,
      execution?.completed_at ?? execution?.created_at ?? "",
      strategy.is_pinned ? "是" : "否",
      strategy.updated_at,
    ];
  }

  function downloadStrategyCsv(strategies: StrategyDetail[], filename: string) {
    downloadCsv(
      [
        [
          "策略名称", "原始研究问题", "框架", "数据库", "当前版本", "检索术语", "MeSH 术语",
          "年份范围", "检索式", "筛选条件", "最新执行状态", "结果数", "最近执行时间", "已置顶", "最后更新",
        ],
        ...strategies.map(strategyExportRow),
      ],
      filename,
    );
  }

  async function refreshSelected() {
    if (selected.value) await select(selected.value.id);
  }

  async function load() {
    const loadId = ++latestLoadId;
    loading.value = true;
    error.value = "";
    try {
      const page = await literatureStrategiesApi.list(offset.value, PAGE_SIZE, filters);
      // 搜索条件可能在请求返回前已改变；仅允许最后一次请求更新页面，避免旧响应回写。
      if (loadId !== latestLoadId) return;
      items.value = page.items;
      total.value = page.total;
      const selectionStillVisible = page.items.some(
        (item) => item.id === selected.value?.id,
      );
      if (!selectionStillVisible) {
        selected.value = null;
        if (page.items[0]) await select(page.items[0].id);
      }
    } catch (cause) {
      if (loadId !== latestLoadId) return;
      error.value = cause instanceof Error ? cause.message : "无法读取检索历史";
    } finally {
      if (loadId === latestLoadId) loading.value = false;
    }
  }

  async function loadProjects() {
    try {
      const response = await researchContextsApi.list();
      projects.value = Array.isArray(response) ? response : [];
    } catch {
      // 项目筛选不是策略列表的阻断依赖；失败时保留“全部项目”。
      projects.value = [];
    }
  }

  async function clone(id: number) {
    const copy = await literatureStrategiesApi.clone(id);
    await load();
    await select(copy.id);
  }

  async function rename(id: number, name: string) {
    await literatureStrategiesApi.patch(id, { name });
    await load();
    if (selected.value?.id === id) await select(id);
  }

  async function moveToProject(id: number, researchContextId: number | null) {
    await literatureStrategiesApi.patch(id, { research_context_id: researchContextId });
    await load();
    if (selected.value?.id === id) await select(id);
  }

  async function rerun() {
    if (!selected.value || rerunning.value) return;
    rerunning.value = true;
    error.value = "";
    try {
      await literatureStrategiesApi.execute(
        selected.value.id,
        selected.value.current_version.version,
      );
      await load();
      await refreshSelected();
    } catch (cause) {
      error.value = cause instanceof ApiError && cause.status === 409
        ? "检索策略已产生新版本，请刷新后重试。"
        : cause instanceof Error ? cause.message : "再次检索失败，请稍后重试";
    } finally {
      rerunning.value = false;
    }
  }

  async function archive(id: number) {
    if (!window.confirm("归档后该策略将从默认列表消失，确认归档吗？")) return;
    await literatureStrategiesApi.archive(id);
    selected.value = null;
    await load();
  }

  async function restore(id: number) {
    await literatureStrategiesApi.restore(id);
    await load();
    if (selected.value?.id === id) await select(id);
  }

  async function exportHistory() {
    const data = await literatureStrategiesApi.exportAll();
    downloadStrategyCsv(
      data.strategies,
      `pubmed-strategies-${new Date().toISOString().slice(0, 10)}.csv`,
    );
  }

  function exportSelected() {
    if (!selected.value) return;
    downloadStrategyCsv(
      [selected.value],
      `pubmed-strategy-${selected.value.id}-v${selected.value.current_version.version}.csv`,
    );
  }

  function goTo(page: number) {
    offset.value = (page - 1) * PAGE_SIZE;
    void load();
  }

  let timer: number | undefined;
  watch(
    filters,
    () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        offset.value = 0;
        void load();
      }, 300);
    },
    { deep: true },
  );
  onMounted(async () => {
    await load();
    await loadProjects();
  });

  return {
    items,
    selected,
    total,
    projects,
    loading,
    detailLoading,
    rerunning,
    error,
    filters,
    currentPage,
    totalPages,
    projectIds,
    load,
    select,
    clearSelection,
    clone,
    rename,
    moveToProject,
    rerun,
    archive,
    restore,
    exportHistory,
    exportSelected,
    goTo,
  };
}
