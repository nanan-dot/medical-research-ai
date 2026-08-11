<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";

import { literatureSearchApi, type LiteratureSearchTask } from "../../api/literatureSearch";
import HistoryPagination from "./HistoryPagination.vue";
import HistoryTableRow from "./HistoryTableRow.vue";

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });
const emit = defineEmits<{ rerunSucceeded: [selection: { resultId: number; taskId: number }] }>();

const pageSize = 10;
const tasks = shallowRef<LiteratureSearchTask[]>([]);
const total = shallowRef(0);
const offset = shallowRef(0);
const isLoading = shallowRef(false);
const rerunningTaskId = shallowRef<number | null>(null);
const requestError = shallowRef("");

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));
const currentPage = computed(() => Math.floor(offset.value / pageSize) + 1);
const hasPreviousPage = computed(() => offset.value > 0);
const hasNextPage = computed(() => offset.value + pageSize < total.value);
interface StrategyGroup {
  key: string;
  summary: string;
  executions: number;
  latestVersion: number;
  tasks: LiteratureSearchTask[];
}

function canonicalSnapshot(value: string): string {
  try {
    return JSON.stringify(JSON.parse(value));
  } catch {
    return value.trim();
  }
}

function strategyKey(task: LiteratureSearchTask): string {
  // 优先使用后端真实策略指纹（与 createTask 的 operation=reused 判定口径一致）；
  // 旧任务或后端未返回时回退到完整策略快照，保证分组不因字段缺失而崩溃。
  return task.strategy_fingerprint
    ?? [
        task.database, task.search_string, canonicalSnapshot(task.filters), task.retmax,
        canonicalSnapshot(task.user_edits), task.model_version, canonicalSnapshot(task.structured_query),
        task.original_query,
      ].join("\u0000");
}

// 按策略分组展示；分组仅改善展示，不写回、不删除、不覆盖审计记录，且默认展开每一条。
const strategyGroups = computed<StrategyGroup[]>(() => {
  const groups = new Map<string, StrategyGroup>();
  for (const task of tasks.value) {
    const key = strategyKey(task);
    const existing = groups.get(key);
    const latestVersion = Math.max(0, ...task.versions.map((version) => version.version));
    if (existing) {
      existing.tasks.push(task);
      existing.executions += task.versions.length || 1;
      existing.latestVersion = Math.max(existing.latestVersion, latestVersion);
    } else {
      groups.set(key, { key, summary: task.search_string, executions: task.versions.length || 1, latestVersion, tasks: [task] });
    }
  }
  return [...groups.values()];
});

async function loadTasks(): Promise<void> {
  isLoading.value = true;
  requestError.value = "";

  try {
    const page = await literatureSearchApi.listTasks(offset.value, pageSize);
    tasks.value = page.items;
    total.value = page.total;
  } catch (cause) {
    requestError.value = cause instanceof Error ? cause.message : "无法读取检索历史";
  } finally {
    isLoading.value = false;
  }
}

function handlePreviousPage(): void {
  if (!hasPreviousPage.value) return;
  offset.value -= pageSize;
  void loadTasks();
}

function handleNextPage(): void {
  if (!hasNextPage.value) return;
  offset.value += pageSize;
  void loadTasks();
}

async function handleRerun(task: LiteratureSearchTask): Promise<void> {
  if (rerunningTaskId.value !== null) return;

  rerunningTaskId.value = task.id;
  requestError.value = "";

  try {
    const { task: updatedTask, new_result_id: newResultId } = await literatureSearchApi.rerunTask(task.id);
    tasks.value = tasks.value.map((item) => (item.id === updatedTask.id ? updatedTask : item));
    emit("rerunSucceeded", { resultId: newResultId, taskId: updatedTask.id });
  } catch (cause) {
    requestError.value = cause instanceof Error ? cause.message : `重跑失败（任务 #${task.id}）`;
  } finally {
    rerunningTaskId.value = null;
  }
}

onMounted(() => {
  void loadTasks();
});
</script>

<template>
  <main class="history-page">
    <header v-if="!props.embedded" class="page-header">
      <h1 class="page-title">历史记录</h1>
      <p class="page-copy">管理您的检索历史。旧的快照将保留，重跑将生成新版本。</p>
    </header>

    <div class="toolbar">
      <button class="refresh-button" type="button" :disabled="isLoading" @click="loadTasks">
        {{ isLoading ? "读取中…" : "刷新" }}
      </button>
      <span class="total-note">共 {{ total }} 次检索 · 当前页展示最近 {{ tasks.length }} 条</span>
    </div>

    <p v-if="requestError" class="request-error" role="alert">{{ requestError }}</p>
    <p v-if="isLoading" class="state-text">正在读取检索历史…</p>
    <p v-else-if="tasks.length === 0 && !requestError" class="empty-state">暂无保存的检索任务…</p>

    <section v-else class="history-table-wrap" aria-label="检索历史列表">
      <div class="history-columns" aria-hidden="true">
        <span>研究主题</span>
        <span>检索式</span>
        <span>结果版本</span>
        <span>结果数</span>
        <span>状态</span>
        <span>最后运行</span>
        <span>操作</span>
      </div>
      <div class="history-list">
        <details v-for="group in strategyGroups" :key="group.key" open class="strategy-group">
          <summary class="strategy-summary">
            <span class="strategy-query">{{ group.summary }}</span>
            <span>执行 {{ group.executions }} 次 · 最新 v{{ group.latestVersion || "—" }}</span>
          </summary>
          <ul class="group-rows">
            <HistoryTableRow
              v-for="task in group.tasks"
              :key="task.id"
              :task="task"
              :is-rerunning="rerunningTaskId === task.id"
              @rerun="handleRerun"
            />
          </ul>
        </details>
      </div>
    </section>

    <HistoryPagination
      v-if="total > pageSize"
      :current-page="currentPage"
      :total-pages="totalPages"
      :is-loading="isLoading"
      :has-previous-page="hasPreviousPage"
      :has-next-page="hasNextPage"
      @previous="handlePreviousPage"
      @next="handleNextPage"
    />
  </main>
</template>

<style scoped>
.history-page { display: grid; gap: 1rem; max-width: 1440px; margin: 0 auto; padding: 1.4rem 1.5rem 2.6rem; }
.page-header { display: grid; gap: .35rem; }
.page-title { margin: 0; color: var(--text-primary); font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1.1; }
.page-copy { max-width: 720px; margin: 0; color: var(--text-muted); line-height: 1.6; }
.toolbar { display: flex; align-items: center; gap: .8rem; }
.refresh-button { padding: .55rem 1rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); color: var(--text-primary); font: inherit; font-weight: 700; cursor: pointer; }
.refresh-button:disabled { cursor: wait; opacity: .6; }
.total-note { color: var(--text-muted); font-size: .86rem; }
.request-error { margin: 0; padding: .8rem; border-radius: 8px; background: var(--color-danger-soft); color: var(--color-danger); }
.state-text { margin: 0; padding: 1.2rem; color: var(--text-muted); }
.empty-state { margin: 0; padding: 2rem; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); color: var(--text-muted); text-align: center; }
.history-table-wrap { overflow-x: auto; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); box-shadow: var(--shadow-card); }
.history-columns { display: grid; grid-template-columns: 1.5fr 1.8fr .8fr .6fr .7fr 1.1fr 1.25fr; gap: .75rem; min-width: 980px; padding: .65rem 1rem; border-bottom: 1px solid var(--border-subtle); background: var(--surface-muted); color: var(--text-muted); font-size: .74rem; font-weight: 700; }
.history-list { margin: 0; padding: 0; }
.strategy-group { border-bottom: 1px solid var(--border-subtle); }
.strategy-group:last-child { border-bottom: 0; }
.strategy-summary { display: flex; align-items: center; justify-content: space-between; gap: 1rem; padding: .65rem 1rem; color: var(--text-primary); background: var(--surface-raised, #f8fafc); cursor: pointer; font-size: .82rem; font-weight: 700; }
.strategy-query { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.group-rows { margin: 0; padding: 0; list-style: none; }
@media (max-width: 900px) { .history-page { padding: 1.2rem; }.history-table-wrap { overflow: visible; }.history-columns { display: none; } }
</style>
