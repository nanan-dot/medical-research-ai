<script setup lang="ts">
import { nextTick, shallowRef } from "vue";

import LiteratureHistoryToolbar from "../../components/literature-history/LiteratureHistoryToolbar.vue";
import LiteratureQuickFilters from "../../components/literature-history/LiteratureQuickFilters.vue";
import LiteratureStrategyCard from "../../components/literature-history/LiteratureStrategyCard.vue";
import LiteratureStrategyDetail from "../../components/literature-history/LiteratureStrategyDetail.vue";
import { useLiteratureHistory } from "../../composables/useLiteratureHistory";
import HistoryPagination from "./HistoryPagination.vue";

withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });
const history = useLiteratureHistory();
const management = shallowRef<{ action: "rename" | "move"; id: number } | null>(null);
const managementValue = shallowRef("");
const managementLoading = shallowRef(false);
const managementError = shallowRef("");
const notice = shallowRef("");
async function closeDetail(): Promise<void> {
  const selectedId = history.selected.value?.id;
  history.clearSelection();
  await nextTick();
  if (selectedId) document.querySelector<HTMLElement>(`[data-strategy-id="${selectedId}"]`)?.focus();
}
function startManagement(action: "rename" | "move", id: number) {
  const strategy = history.items.value.find((item) => item.id === id) ?? history.selected.value;
  management.value = { action, id };
  managementValue.value = action === "rename" ? strategy?.name ?? "" : String(strategy?.research_context_id ?? "");
  managementError.value = "";
}
async function handleAction(action: "rename" | "move" | "clone" | "archive" | "restore", id: number) {
  notice.value = "";
  if (action === "rename" || action === "move") return startManagement(action, id);
  try {
    if (action === "clone") { await history.clone(id); notice.value = "已创建策略副本。"; }
    if (action === "archive") { await history.archive(id); notice.value = "策略已归档。"; }
    if (action === "restore") { await history.restore(id); notice.value = "策略已恢复。"; }
  } catch (cause) { history.error.value = cause instanceof Error ? cause.message : "操作失败，请稍后重试"; }
}
async function saveManagement() {
  if (!management.value || managementLoading.value) return;
  managementLoading.value = true; managementError.value = "";
  try {
    if (management.value.action === "rename") {
      const name = managementValue.value.trim();
      if (!name) { managementError.value = "请输入策略名称。"; return; }
      await history.rename(management.value.id, name);
      notice.value = "策略名称已更新。";
    } else {
      await history.moveToProject(management.value.id, managementValue.value ? Number(managementValue.value) : null);
      notice.value = "策略所属项目已更新。";
    }
    management.value = null;
  } catch (cause) { managementError.value = cause instanceof Error ? cause.message : "保存失败，请稍后重试"; }
  finally { managementLoading.value = false; }
}
</script>

<template>
  <main class="history-page">
    <header class="page-header">
      <div><p class="breadcrumb">‹　文献检索　/　<b>检索历史</b></p><h1>检索历史</h1><span>查看、复用和比较过去的 PubMed 检索策略</span></div>
      <button class="export" type="button" @click="history.exportHistory">⇩　导出历史记录</button>
    </header>
    <div class="workspace">
      <section class="list-pane" aria-label="检索策略列表">
        <LiteratureHistoryToolbar v-model:query="history.filters.query" v-model:research-context-id="history.filters.researchContextId" v-model:framework="history.filters.framework" v-model:time-range="history.filters.timeRange" v-model:archived="history.filters.archived" :projects="history.projects.value" />
        <LiteratureQuickFilters v-model="history.filters.quickFilter" />
        <div class="list-heading">
          <b>{{ history.total.value }} 个检索策略</b>
          <div class="sort-control">
            <span class="sort-label">排序</span>
            <label class="sort-select">
              <span class="sort-icon" aria-hidden="true">⇅</span>
              <select v-model="history.filters.sort" aria-label="检索策略排序方式">
                <option value="updated_at">最近更新</option>
                <option value="created_at">最近创建</option>
                <option value="name">名称排序</option>
              </select>
              <span class="sort-chevron" aria-hidden="true">⌄</span>
            </label>
          </div>
        </div>
        <p v-if="history.error.value" role="alert" class="error">{{ history.error.value }}</p><p v-if="notice" role="status" class="notice">{{ notice }}</p>
        <div v-if="history.loading.value" class="skeletons" aria-live="polite"><span v-for="index in 5" :key="index" /></div>
        <div v-else-if="history.items.value.length" class="cards"><LiteratureStrategyCard v-for="item in history.items.value" :key="item.id" :item="item" :active="history.selected.value?.id === item.id" @select="history.select" @action="handleAction" @rerun="history.rerun" /></div>
        <div v-else class="empty"><b>没有匹配的检索策略</b><span>调整搜索词或筛选条件后重试。</span></div>
        <HistoryPagination v-if="history.totalPages.value > 1" :current-page="history.currentPage.value" :total-pages="history.totalPages.value" :total="history.total.value" :is-loading="history.loading.value" :has-previous-page="history.currentPage.value > 1" :has-next-page="history.currentPage.value < history.totalPages.value" @previous="history.goTo(history.currentPage.value - 1)" @next="history.goTo(history.currentPage.value + 1)" @page="history.goTo" />
      </section>
      <LiteratureStrategyDetail class="history-detail" :class="{ 'has-selection': Boolean(history.selected.value) || history.detailLoading.value }" :task="history.selected.value" :loading="history.detailLoading.value" :rerunning="history.rerunning.value" @action="handleAction" @rerun="history.rerun" @export="history.exportSelected" @close="closeDetail" />
    </div>
    <dialog :open="Boolean(management)" aria-labelledby="management-title" @close="management = null">
      <form v-if="management" method="dialog" @submit.prevent="saveManagement">
        <h2 id="management-title">{{ management.action === 'rename' ? '重命名策略' : '移动到研究项目' }}</h2>
        <label v-if="management.action === 'rename'" for="strategy-name">策略名称<input id="strategy-name" v-model="managementValue" :disabled="managementLoading" required /></label>
        <label v-else for="strategy-project">研究项目<select id="strategy-project" v-model="managementValue" :disabled="managementLoading"><option value="">不关联项目</option><option v-for="project in history.projects.value" :key="project.id" :value="String(project.id)">{{ project.name }}</option></select></label>
        <p v-if="managementError" role="alert" class="error">{{ managementError }}</p>
        <footer><button type="button" :disabled="managementLoading" @click="management = null">取消</button><button class="primary" type="submit" :disabled="managementLoading">{{ managementLoading ? '保存中…' : '保存' }}</button></footer>
      </form>
    </dialog>
  </main>
</template>

<style scoped>
.history-page {
  height: 100%;
  min-height: 100vh;
  background: var(--surface-muted);
}

.page-header {
  display: flex;
  min-height: 126px;
  align-items: center;
  justify-content: space-between;
  margin-right: 472px;
  padding: 18px 26px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface);
}

.breadcrumb,
.page-header h1,
.page-header span {
  margin: 0;
}

.breadcrumb,
.page-header span {
  color: var(--text-muted);
  font-size: 11px;
}

.page-header h1 {
  margin: 6px 0;
  color: var(--text-primary);
  font-size: 25px;
  line-height: 1.2;
}

.export {
  width: 120px;
  min-height: 34px;
  padding: 0;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-primary);
  font: 700 12px inherit;
  cursor: pointer;
}

.workspace {
  display: grid;
  grid-template-columns: minmax(580px, 1fr) 472px;
  height: calc(100vh - 126px);
}

.list-pane {
  min-width: 0;
  padding: 20px 20px 14px 26px;
  overflow: auto;
}

.list-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 19px 0 10px;
}

.list-heading > b {
  color: var(--text-primary);
  font-size: 13px;
}

.sort-control {
  display: flex;
  gap: 8px;
  align-items: center;
}

.sort-label {
  color: var(--text-secondary);
  font-size: 11px;
}

.sort-select {
  display: grid;
  grid-template-columns: auto minmax(72px, auto) auto;
  min-height: 32px;
  align-items: center;
  gap: 6px;
  padding: 0 9px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text-primary);
}

.sort-select:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px var(--color-primary-soft);
}

.sort-select select {
  min-width: 0;
  border: 0;
  outline: 0;
  appearance: none;
  background: transparent;
  color: inherit;
  font: 700 11px/1 inherit;
  cursor: pointer;
}

.sort-icon,
.sort-chevron {
  color: var(--text-muted);
  font-size: 11px;
  pointer-events: none;
}

.cards,
.skeletons {
  display: grid;
  gap: 9px;
}

.error {
  margin: 0 0 10px;
  padding: 9px;
  border-radius: 6px;
  background: var(--color-danger-soft);
  color: var(--color-danger);
  font-size: 12px;
}
.notice { margin:0 0 10px; color:var(--color-success); font-size:12px; }
dialog { width:min(390px, calc(100vw - 32px)); border:1px solid var(--border-subtle); border-radius:10px; box-shadow:var(--shadow-md); } dialog form { display:grid; gap:14px; } dialog h2 { margin:0; font-size:16px; } dialog label { display:grid; gap:6px; color:var(--text-secondary); font-size:12px; font-weight:700; } dialog input,dialog select { min-height:34px; border:1px solid var(--border-subtle); border-radius:6px; padding:0 8px; background:var(--surface); color:var(--text-primary); font:inherit; } dialog footer { display:flex; justify-content:flex-end; gap:8px; } dialog footer button { min-height:32px; padding:0 12px; border:1px solid var(--border-subtle); border-radius:6px; background:var(--surface); font:700 12px inherit; cursor:pointer; } dialog .primary { border-color:var(--color-primary); background:var(--color-primary); color:#fff; } dialog::backdrop { background:rgb(20 45 90 / 24%); }

.empty {
  display: grid;
  min-height: 220px;
  place-content: center;
  gap: 5px;
  color: var(--text-muted);
  text-align: center;
  font-size: 12px;
}

.skeletons span {
  display: block;
  height: 108px;
  border-radius: 8px;
  background: linear-gradient(90deg, #edf1f7 25%, #f6f8fb 50%, #edf1f7 75%);
  background-size: 200% 100%;
  animation: loading 1.3s infinite;
}

.workspace :deep(.history-detail) {
  position: fixed;
  z-index: 10;
  top: 12px;
  right: 12px;
  width: 448px;
  height: calc(100vh - 24px);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  box-shadow: -8px 12px 30px rgb(20 45 90 / 8%);
}

@keyframes loading {
  to { background-position: -200% 0; }
}

@media (max-width: 1100px) {
  .page-header { margin-right: 0; }
  .workspace { grid-template-columns: 1fr; }
  .workspace :deep(.history-detail) {
    width: min(448px, calc(100vw - 24px));
    box-shadow: -8px 12px 30px rgb(20 45 90 / 12%);
  }
  .workspace :deep(.history-detail:not(.has-selection)) { display: none; }
}

@media (max-width: 768px) {
  .page-header { padding: 13px 15px; }
  .page-header span { display: none; }
  .workspace { height: calc(100vh - 69px); }
  .list-pane { padding: 15px; }
  .export {
    width: 34px;
    padding: 0;
    font-size: 0;
  }
  .export::first-letter { font-size: 14px; }
}
</style>
