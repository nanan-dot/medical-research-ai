<script setup lang="ts">
// 进行中的工作：从真实后端读取文献检索任务的运行/失败状态。
// 无运行中任务时显示空态；重试调用真实 rerun 接口。
import { onMounted, shallowRef } from "vue";
import { MAX_SEARCH_RESULTS, literatureSearchApi, type LiteratureSearchTask } from "../../api/literatureSearch";

interface ActiveTask {
  id: number;
  kind: string;
  title: string;
  state: "running" | "failed" | "queued";
  detail: string;
}

const loading = shallowRef(true);
const error = shallowRef("");
const tasks = shallowRef<ActiveTask[]>([]);

async function load(): Promise<void> {
  loading.value = true;
  error.value = "";
  try {
    const page = await literatureSearchApi.listTasks(0, 20);
    const active = page.items.filter((task) => ["pending", "running", "failed"].includes(task.status));
    tasks.value = active.slice(0, 4).map((task) => toView(task));
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取任务状态";
  } finally {
    loading.value = false;
  }
}

function toView(task: LiteratureSearchTask): ActiveTask {
  const kind = task.database === "pubmed" ? "检索" : "任务";
  const state = task.status === "failed" ? "failed" : task.status === "running" ? "running" : "queued";
  const detail = task.status === "failed" ? `失败（${task.error_message ?? "未知原因"}）` : task.status === "running" ? "正在检索中…" : "排队中…";
  return { id: task.id, kind, title: task.original_query, state, detail };
}

onMounted(load);

async function retryTask(task: ActiveTask): Promise<void> {
  error.value = "";
  try {
    await literatureSearchApi.rerunTask(task.id, MAX_SEARCH_RESULTS);
    await load();
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "重试失败";
  }
}
</script>

<template>
  <section class="work-panel" aria-label="进行中的工作">
    <div class="panel-head">
      <h2 class="panel-title">进行中的工作</h2>
      <RouterLink class="more" to="/tasks">全部任务 →</RouterLink>
    </div>

    <p v-if="loading" class="hint">正在读取任务状态…</p>
    <p v-else-if="error" class="hint error">{{ error }}</p>
    <p v-else-if="!tasks.length" class="hint empty">当前没有进行中的任务。</p>

    <ul v-else class="task-list">
      <li v-for="task in tasks" :key="task.id" class="task" :class="task.state">
        <div class="task-line">
          <span class="task-dot" aria-hidden="true"></span>
          <span class="task-title">{{ task.kind }}：{{ task.title }}</span>
        </div>
        <div class="task-foot">
          <span class="task-detail" :class="task.state">{{ task.detail }}</span>
          <button
            v-if="task.state === 'failed'"
            type="button"
            class="retry"
            aria-label="重试任务"
            @click="retryTask(task)"
          >
            ↻ 重试
          </button>
        </div>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.work-panel {
  min-width: 0;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
  margin-bottom: 0.7rem;
}
.panel-title {
  margin: 0;
  color: var(--text-primary);
  font-size: 1rem;
}
.more {
  color: var(--text-muted);
  font-size: 0.78rem;
  text-decoration: none;
}
.more:hover,
.more:focus-visible {
  color: var(--color-primary);
}
.hint {
  margin: 0;
  padding: 1rem;
  color: var(--text-muted);
  font-size: 0.84rem;
  background: var(--surface);
  border: 1px dashed var(--border-subtle);
  border-radius: 10px;
}
.hint.error {
  color: var(--color-danger);
}
.hint.empty {
  color: var(--text-faint);
}
.task-list {
  display: grid;
  gap: 0.7rem;
  margin: 0;
  padding: 0;
  list-style: none;
}
.task {
  position: relative;
  padding: 0.85rem 0.95rem;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
}
.task-line {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}
.task-dot {
  flex-shrink: 0;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.task.running .task-dot {
  background: var(--color-success);
  box-shadow: 0 0 0 3px rgba(22, 163, 74, 0.14);
}
.task.failed .task-dot {
  background: var(--color-danger);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.14);
}
.task.queued .task-dot {
  background: var(--color-warning);
  box-shadow: 0 0 0 3px rgba(217, 119, 6, 0.14);
}
.task-title {
  min-width: 0;
  color: var(--text-primary);
  font-size: 0.85rem;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.task-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.6rem;
  margin-top: 0.35rem;
}
.task-detail {
  color: var(--text-muted);
  font-size: 0.76rem;
}
.task-detail.failed {
  color: var(--color-danger);
}
.retry {
  flex-shrink: 0;
  padding: 0.28rem 0.65rem;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  background: var(--surface);
  color: var(--text-primary);
  font-size: 0.76rem;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s;
}
.retry:hover,
.retry:focus-visible {
  border-color: var(--color-danger);
  color: var(--color-danger);
  outline: none;
}
</style>
