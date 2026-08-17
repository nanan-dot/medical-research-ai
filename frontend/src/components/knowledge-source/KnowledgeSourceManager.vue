<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { useRouter } from "vue-router";

import { knowledgeSourcesApi, type CreateKnowledgeSource, type KnowledgeSource } from "../../api/knowledgeSources";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";
import KnowledgeSourceForm from "./KnowledgeSourceForm.vue";
import KnowledgeSourceList from "./KnowledgeSourceList.vue";
import SingleDocumentImportPanel from "./SingleDocumentImportPanel.vue";

type SourceFilter = "all" | "enabled" | "errors" | "recent";

const SOURCE_FILTERS: ReadonlyArray<{ value: SourceFilter; label: string }> = [
  { value: "all", label: "全部" },
  { value: "enabled", label: "已启用" },
  { value: "errors", label: "异常" },
  { value: "recent", label: "最近同步" },
];

const router = useRouter();
const { sources, loading, error, enabledCount, load, create, setEnabled, remove, sync } = useKnowledgeSources();
const activeFilter = shallowRef<SourceFilter>("all");
const isCreateDrawerOpen = shallowRef(false);
const isImportChooserOpen = shallowRef(false);
const isDocumentImportOpen = shallowRef(false);
const isImportingDocument = shallowRef(false);
const documentImportError = shallowRef<string | null>(null);
const isNewestFirst = shallowRef(true);
const pendingRemovalId = shallowRef<number | null>(null);

const filteredSources = computed(() => {
  const candidates = sources.value.filter((source) => {
    if (activeFilter.value === "enabled") return source.enabled;
    if (activeFilter.value === "errors") return ["completed_with_errors", "unavailable"].includes(source.sync_status);
    return true;
  });

  if (activeFilter.value !== "recent") return candidates;
  return [...candidates].sort((left, right) => compareSyncTime(left, right, isNewestFirst.value));
});

function compareSyncTime(left: KnowledgeSource, right: KnowledgeSource, newestFirst: boolean): number {
  const leftTime = left.last_sync_time ? Date.parse(left.last_sync_time) : Number.NEGATIVE_INFINITY;
  const rightTime = right.last_sync_time ? Date.parse(right.last_sync_time) : Number.NEGATIVE_INFINITY;
  return newestFirst ? rightTime - leftTime : leftTime - rightTime;
}

async function submitSource(payload: CreateKnowledgeSource): Promise<void> {
  await create(payload);
  if (!error.value) isCreateDrawerOpen.value = false;
}

async function submitDocumentImport(payload: { file: File; knowledgeSourceId?: number; newSourceName?: string; relativeDirectory?: string }): Promise<void> {
  isImportingDocument.value = true;
  documentImportError.value = null;
  try {
    const result = await knowledgeSourcesApi.importDocument(payload);
    isDocumentImportOpen.value = false;
    await load();
    await router.push({ path: "/documents", query: { sourceId: String(result.knowledge_source_id) } });
  } catch (importError) {
    documentImportError.value = importError instanceof Error ? importError.message : "文档导入失败";
  } finally {
    isImportingDocument.value = false;
  }
}

function confirmRemove(source: KnowledgeSource): void {
  if (pendingRemovalId.value === source.id) {
    pendingRemovalId.value = null;
    void remove(source);
    return;
  }

  pendingRemovalId.value = source.id;
}

function openDocuments(source: KnowledgeSource): void {
  void router.push({ path: "/documents", query: { sourceId: String(source.id) } });
}

onMounted(() => void load());
</script>

<template>
  <section class="manager" aria-labelledby="manager-title">
    <div class="toolbar">
      <div class="filter-tabs" role="tablist" aria-label="知识源筛选">
        <button
          v-for="filter in SOURCE_FILTERS"
          :key="filter.value"
          type="button"
          role="tab"
          :aria-selected="activeFilter === filter.value"
          :class="{ active: activeFilter === filter.value }"
          @click="activeFilter = filter.value"
        >
          {{ filter.label }}
        </button>
      </div>
      <button class="primary-action" type="button" @click="isImportChooserOpen = true">
        导入资料
      </button>
    </div>

    <header class="manager-header">
      <div>
        <h2 id="manager-title">知识来源</h2>
        <p>{{ loading ? "正在读取" : `${sources.length} 个来源 · ${enabledCount} 个已启用` }}</p>
      </div>
      <button class="sort-action" type="button" @click="isNewestFirst = !isNewestFirst">
        按最近同步排序 {{ isNewestFirst ? "↓" : "↑" }}
      </button>
    </header>

    <p v-if="error" class="request-error" role="alert">
      {{ error }}
      <button type="button" @click="load">重试</button>
    </p>
    <div v-else-if="loading && sources.length === 0" class="loading-state" role="status">
      <span v-for="item in 3" :key="item" class="skeleton-row" aria-hidden="true" />
      <span class="sr-only">正在读取知识来源…</span>
    </div>
    <KnowledgeSourceList
      v-else
      :sources="filteredSources"
      :disabled="loading"
      :pending-removal-id="pendingRemovalId"
      @toggle="setEnabled"
      @remove="confirmRemove"
      @sync="sync"
      @view-documents="openDocuments"
    />

    <aside v-if="isImportChooserOpen" class="drawer" aria-label="导入资料">
      <header class="drawer-header"><div><h3>导入资料</h3><p>选择要导入的资料类型。</p></div><button aria-label="关闭抽屉" type="button" @click="isImportChooserOpen = false">×</button></header>
      <div class="import-choice"><button type="button" @click="isImportChooserOpen = false; isCreateDrawerOpen = true">导入资料文件夹</button><button type="button" @click="isImportChooserOpen = false; isDocumentImportOpen = true">导入单篇文档</button></div>
    </aside>

    <aside v-if="isCreateDrawerOpen" class="drawer" aria-label="添加资料文件夹">
      <header class="drawer-header">
        <div>
          <h3>添加资料文件夹</h3>
          <p>只添加系统记录，不会读取或上传目录外内容。</p>
        </div>
        <button aria-label="关闭抽屉" type="button" @click="isCreateDrawerOpen = false">×</button>
      </header>
      <KnowledgeSourceForm :disabled="loading" @submit="submitSource" />
    </aside>

    <aside v-if="isDocumentImportOpen" class="drawer" aria-label="导入单篇文档">
      <header class="drawer-header"><div><h3>导入单篇文档</h3><p>每篇文档都必须归属一个知识库。</p></div><button aria-label="关闭抽屉" type="button" :disabled="isImportingDocument" @click="isDocumentImportOpen = false">×</button></header>
      <SingleDocumentImportPanel :sources="sources" :submitting="isImportingDocument" :error="documentImportError" @close="isDocumentImportOpen = false" @submit="submitDocumentImport" />
    </aside>
  </section>
</template>

<style scoped>
.manager {
  position: relative;
  margin-top: 20px;
  padding: 20px 26px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--surface-raised);
  box-shadow: var(--shadow-card);
}

.toolbar,
.manager-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.filter-tabs {
  display: flex;
  padding: 3px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}

.filter-tabs button,
.sort-action {
  border: 0;
  border-radius: 6px;
  padding: 7px 11px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-size: 0.8rem;
  font-weight: 700;
}

.filter-tabs button.active {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}

.primary-action {
  border: 0;
  border-radius: 8px;
  padding: 9px 13px;
  background: var(--color-primary);
  color: var(--surface);
  font-weight: 700;
}

.manager-header {
  margin: 20px 0 13px;
}

.manager-header h2 {
  margin: 0;
  color: var(--ink-900);
  font-size: 1.1rem;
}

.manager-header p,
.drawer p {
  margin: 2px 0 0;
  color: var(--text-muted);
  font-size: 0.8rem;
}

.sort-action {
  border: 1px solid var(--border-subtle);
  color: var(--ink-900);
}

.request-error,
.loading-state {
  margin: 0;
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}

.request-error {
  color: var(--color-danger);
  background: var(--color-danger-soft);
}

.request-error button {
  margin-left: 8px;
  border: 0;
  background: transparent;
  color: inherit;
  font-weight: 700;
}

.loading-state {
  display: grid;
  gap: 10px;
  background: var(--surface-muted);
}

.skeleton-row {
  display: block;
  height: 18px;
  border-radius: 5px;
  background: var(--border-subtle);
}

.skeleton-row:nth-child(2) {
  width: 82%;
}

.skeleton-row:nth-child(3) {
  width: 65%;
}

.drawer {
  position: absolute;
  z-index: 4;
  top: 0;
  right: 0;
  width: min(100%, 500px);
  padding: 22px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: 0 16px 36px rgb(15 23 42 / 16%);
}

.drawer-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.drawer h3 {
  margin: 0;
  font-size: 1.1rem;
}

.drawer-header button {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 1.5rem;
}

.import-choice { display: grid; gap: 10px; }
.import-choice button { border: 1px solid var(--border-subtle); border-radius: 8px; padding: 12px; background: var(--surface-muted); color: var(--ink-900); font: inherit; font-weight: 700; text-align: left; }

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
}

@media (max-width: 700px) {
  .toolbar,
  .manager-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .primary-action,
  .filter-tabs {
    width: 100%;
  }

  .filter-tabs {
    overflow: auto;
  }

  .drawer {
    position: fixed;
    inset: auto 0 0;
    width: 100%;
    border-radius: 12px 12px 0 0;
  }
}
</style>
