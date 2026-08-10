<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { literatureSearchApi, type LiteratureSearchTask, type SearchResultChange } from "../../api/literatureSearch";
const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });

// 每页条数：后端分页默认 20，这里取 10 便于快速翻页。
const PAGE_SIZE = 10;

const items = shallowRef<LiteratureSearchTask[]>([]);
const total = shallowRef(0);
const offset = shallowRef(0);
const loading = shallowRef(false);
const rerunning = shallowRef<number | null>(null);
const error = shallowRef("");

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)));
const currentPage = computed(() => Math.floor(offset.value / PAGE_SIZE) + 1);

const statusLabels: Record<string, string> = {
  pending: "待执行",
  running: "执行中",
  succeeded: "已完成",
  failed: "失败",
};

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const page = await literatureSearchApi.listTasks(offset.value, PAGE_SIZE);
    items.value = page.items;
    total.value = page.total;
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取检索历史";
  } finally {
    loading.value = false;
  }
}

function prevPage() {
  if (offset.value <= 0) return;
  offset.value -= PAGE_SIZE;
  void load();
}

function nextPage() {
  if (offset.value + PAGE_SIZE >= total.value) return;
  offset.value += PAGE_SIZE;
  void load();
}

async function rerun(task: LiteratureSearchTask) {
  if (rerunning.value !== null) return;
  rerunning.value = task.id;
  error.value = "";
  try {
    const { task: updated } = await literatureSearchApi.rerunTask(task.id);
    // 用服务端返回的最新任务替换列表项，变化摘要来自其最新版本。
    items.value = items.value.map((item) => (item.id === updated.id ? updated : item));
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : `重跑失败（任务 #${task.id}）`;
  } finally {
    rerunning.value = null;
  }
}

// 最近一次版本相对上一版本的变化；首个版本（无基线）返回 null。
function latestChange(task: LiteratureSearchTask): SearchResultChange | null {
  return task.versions.at(-1)?.change ?? null;
}

// 检索日期取最近一次成功执行的 searched_at；从未成功时如实显示"未检索"。
function searchDate(task: LiteratureSearchTask): string {
  if (!task.searched_at) return "未检索";
  return new Date(task.searched_at).toLocaleString("zh-CN", { hour12: false });
}

function createdDate(task: LiteratureSearchTask): string {
  return new Date(task.created_at).toLocaleString("zh-CN", { hour12: false });
}

onMounted(load);
</script>

<template>
  <main class="history">
    <header v-if="!props.embedded" class="page-header">
      <p class="eyebrow">SEARCH HISTORY · LIVE</p>
      <h1 class="page-title">检索历史</h1>
      <p class="page-copy">已保存的可复现检索任务：主题、检索式、检索日期、结果数与执行状态。重跑会创建新版本，不覆盖旧结果；新旧版本的变化会明确提示。</p>
    </header>

    <div class="toolbar">
      <button :disabled="loading" @click="load">{{ loading ? "读取中…" : "刷新" }}</button>
      <span v-if="!loading" class="total-note">共 {{ total }} 次检索</span>
    </div>
    <p v-if="error" class="request-error" role="alert">{{ error }}</p>

    <p v-if="loading" class="state-text">正在读取检索历史…</p>
    <p v-else-if="items.length === 0 && !error" class="empty-state">暂无保存的检索任务。任务由后端检索执行接口（POST /literature-search）记录，完成后会显示在这里。</p>

    <ul v-else class="history-list">
      <li v-for="task in items" :key="task.id" class="history-item">
        <div class="item-head">
          <span class="status-badge" :class="`status-${task.status}`">{{ statusLabels[task.status] }}</span>
          <h2 class="item-title">{{ task.original_query }}</h2>
          <RouterLink v-if="task.latest_result_id" class="view-results" :to="`/literature-search/results/${task.latest_result_id}?task=${task.id}`">查看结果</RouterLink>
          <button class="rerun" :disabled="rerunning === task.id || task.status === 'running'" @click="rerun(task)">
            {{ rerunning === task.id ? "重跑中…" : "重跑" }}
          </button>
        </div>
        <p class="search-string" :title="task.search_string">{{ task.search_string }}</p>
        <dl class="meta-row">
          <div><dt>检索日期</dt><dd>{{ searchDate(task) }}</dd></div>
          <div><dt>创建时间</dt><dd>{{ createdDate(task) }}</dd></div>
          <div><dt>结果数</dt><dd>{{ task.result_count }}</dd></div>
          <div><dt>数据库</dt><dd>{{ task.database }}</dd></div>
          <div><dt>模型版本</dt><dd>{{ task.model_version }}</dd></div>
          <div><dt>版本数</dt><dd>{{ task.versions.length }}</dd></div>
        </dl>
        <p v-if="task.error_message" class="task-error" role="alert">失败原因：{{ task.error_message }}</p>
        <div v-if="latestChange(task)" class="change-summary" :class="latestChange(task)!.count_delta < 0 ? 'decreased' : 'increased'">
          <span>相对上次：命中数 {{ latestChange(task)!.previous_count }} → {{ latestChange(task)!.current_count }}，新增 {{ latestChange(task)!.added_count }} 条，减少 {{ latestChange(task)!.removed_count }} 条</span>
          <span v-if="latestChange(task)!.added_pmids.length" class="pmids">新增 PMID：{{ latestChange(task)!.added_pmids.join(", ") }}</span>
          <span v-if="latestChange(task)!.removed_pmids.length" class="pmids">减少 PMID：{{ latestChange(task)!.removed_pmids.join(", ") }}</span>
        </div>
      </li>
    </ul>

    <nav v-if="total > PAGE_SIZE" class="pagination" aria-label="历史分页">
      <button :disabled="offset === 0 || loading" @click="prevPage">上一页</button>
      <span class="page-note">第 {{ currentPage }} / {{ totalPages }} 页</span>
      <button :disabled="offset + PAGE_SIZE >= total || loading" @click="nextPage">下一页</button>
    </nav>
  </main>
</template>

<style scoped>
.history { max-width: 1000px; margin: auto; padding: 2rem 1.4rem 3rem; display: grid; gap: 1rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-weight: 800; letter-spacing: .12em; font-size: .72rem; }
.page-title { margin: .25rem 0; color: var(--text-primary); font-size: clamp(2rem, 4vw, 3.2rem); line-height: 1.1; }
.page-copy { max-width: 720px; color: var(--text-muted); line-height: 1.6; }

.toolbar { display: flex; align-items: center; gap: .8rem; }
.toolbar button { padding: .55rem 1rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); color: var(--text-primary); font-weight: 700; }
.toolbar button:disabled { opacity: .6; }
.total-note { color: var(--text-muted); font-size: .86rem; }

.request-error { margin: 0; padding: .8rem; color: var(--color-danger); background: var(--color-danger-soft); border-radius: 10px; }
.state-text { padding: 1.2rem; color: var(--text-muted); }
.empty-state { padding: 2rem; border: 1px dashed var(--border-strong); border-radius: var(--radius-md); text-align: center; color: var(--text-muted); }

.history-list { list-style: none; margin: 0; padding: 0; display: grid; gap: .8rem; }
.history-item { display: grid; gap: .7rem; padding: 1rem 1.1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); box-shadow: var(--shadow); }
.item-head { display: flex; align-items: center; gap: .7rem; flex-wrap: wrap; }
.item-title { margin: 0; font-size: 1.12rem; color: var(--text-primary); word-break: break-word; flex: 1; min-width: 0; }
.status-badge { display: inline-block; border-radius: 99px; padding: .25rem .6rem; background: var(--surface-muted); font-size: .75rem; font-weight: 800; white-space: nowrap; }
.status-succeeded { background: var(--color-success-soft); color: var(--color-success); }
.status-failed { background: var(--color-danger-soft); color: var(--color-danger); }
.status-running, .status-pending { background: var(--color-primary-soft); color: var(--color-primary); }
.rerun { padding: .45rem .8rem; border: 0; border-radius: 8px; background: var(--color-primary); color: #fff; font-weight: 750; }
.rerun:disabled { opacity: .6; }
.view-results { padding: .45rem .8rem; border: 1px solid var(--color-primary); border-radius: 8px; color: var(--color-primary); font-weight: 750; text-decoration: none; white-space: nowrap; }
.view-results:hover { background: var(--color-primary-soft); }

.search-string { margin: 0; padding: .6rem .75rem; border-radius: 8px; background: var(--surface-muted); color: var(--text-muted); font-family: ui-monospace, "SF Mono", Consolas, monospace; font-size: .8rem; overflow-wrap: anywhere; }

.meta-row { display: flex; flex-wrap: wrap; gap: 1.1rem; margin: 0; padding-top: .5rem; border-top: 1px solid var(--border-subtle); }
.meta-row div { display: grid; gap: .1rem; }
.meta-row dt { font-size: .7rem; color: var(--text-faint); }
.meta-row dd { margin: 0; font-size: .84rem; color: var(--text-primary); }

.task-error { margin: 0; color: var(--color-danger); font-size: .84rem; }
.change-summary { display: grid; gap: .2rem; padding: .7rem .8rem; border-radius: 8px; background: var(--color-primary-soft); color: var(--color-primary); font-size: .82rem; }
.change-summary.decreased { background: var(--color-warning-soft); color: var(--color-warning); }
.change-summary .pmids { color: var(--text-muted); overflow-wrap: anywhere; }

.pagination { display: flex; align-items: center; justify-content: center; gap: .8rem; }
.pagination button { padding: .5rem .85rem; border: 1px solid var(--border-strong); border-radius: 8px; background: var(--surface); color: var(--text-primary); font-weight: 700; }
.pagination button:disabled { opacity: .5; }
.page-note { color: var(--text-muted); font-size: .86rem; }
</style>
