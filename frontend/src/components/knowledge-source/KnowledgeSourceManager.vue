<script setup lang="ts">
import { computed, onMounted, shallowRef } from "vue";
import { useRouter } from "vue-router";

import type { CreateKnowledgeSource, KnowledgeSource } from "../../api/knowledgeSources";
import { useKnowledgeSources } from "../../composables/useKnowledgeSources";
import KnowledgeSourceForm from "./KnowledgeSourceForm.vue";
import KnowledgeSourceList from "./KnowledgeSourceList.vue";

type SourceFilter = "all" | "enabled" | "errors" | "recent";

const router = useRouter();
const { sources, loading, error, enabledCount, load, create, setEnabled, remove, sync } = useKnowledgeSources();
const activeFilter = shallowRef<SourceFilter>("all");
const isCreateDrawerOpen = shallowRef(false);
const isNewestFirst = shallowRef(true);

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

function confirmRemove(source: KnowledgeSource): void {
  const accepted = window.confirm(`确认移除“${source.name}”吗？仅移除系统记录，不会删除原始目录中的文件。`);
  if (accepted) void remove(source);
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
        <button v-for="filter in [{ value: 'all', label: '全部' }, { value: 'enabled', label: '已启用' }, { value: 'errors', label: '异常' }, { value: 'recent', label: '最近同步' }]" :key="filter.value" type="button" :class="{ active: activeFilter === filter.value }" @click="activeFilter = filter.value as SourceFilter">{{ filter.label }}</button>
      </div>
      <button class="primary-action" type="button" @click="isCreateDrawerOpen = true">＋ 添加资料文件夹</button>
    </div>
    <header class="manager-header"><div><h2 id="manager-title">知识来源</h2><p>{{ loading ? "正在读取" : `${sources.length} 个来源 · ${enabledCount} 个已启用` }}</p></div><button class="sort-action" type="button" @click="isNewestFirst = !isNewestFirst">按最近同步排序 {{ isNewestFirst ? "↓" : "↑" }}</button></header>
    <p v-if="error" class="request-error" role="alert">{{ error }} <button type="button" @click="load">重试</button></p>
    <p v-else-if="loading && sources.length === 0" class="loading-state">正在读取知识来源…</p>
    <KnowledgeSourceList v-else :sources="filteredSources" :disabled="loading" @toggle="setEnabled" @remove="confirmRemove" @sync="sync" @view-documents="openDocuments" />
    <aside v-if="isCreateDrawerOpen" class="drawer" aria-label="添加资料文件夹"><header><div><h3>添加资料文件夹</h3><p>只添加系统记录，不会读取或上传目录外内容。</p></div><button aria-label="关闭抽屉" type="button" @click="isCreateDrawerOpen = false">×</button></header><KnowledgeSourceForm :disabled="loading" @submit="submitSource" /></aside>
  </section>
</template>

<style scoped>
.manager{position:relative;margin-top:20px;padding:20px 26px;border:1px solid var(--border-subtle);border-radius:12px;background:var(--surface-raised);box-shadow:0 1px 2px rgba(16,33,61,.04),0 4px 16px rgba(16,33,61,.03)}.toolbar,.manager-header{display:flex;align-items:center;justify-content:space-between;gap:16px}.filter-tabs{display:flex;padding:3px;border:1px solid var(--border-subtle);border-radius:8px}.filter-tabs button,.sort-action{border:0;border-radius:6px;padding:7px 11px;background:transparent;color:var(--text-muted);font:inherit;font-size:.8rem;font-weight:700}.filter-tabs button.active{background:var(--color-primary-soft);color:var(--color-primary)}.primary-action{border:0;border-radius:8px;padding:9px 13px;background:var(--color-primary);color:#fff;font-weight:700}.manager-header{margin:20px 0 13px}.manager-header h2{margin:0;color:var(--ink-900,#10213d);font-size:1.1rem}.manager-header p{margin:2px 0 0;color:var(--text-muted);font-size:.8rem}.sort-action{border:1px solid var(--border-subtle);color:var(--ink-900,#10213d)}.request-error,.loading-state{margin:0;padding:14px;border:1px solid var(--border-subtle);border-radius:8px;color:var(--color-danger);background:var(--color-danger-soft)}.request-error button{margin-left:8px;border:0;background:transparent;color:inherit;font-weight:700}.loading-state{color:var(--text-muted);background:#fafcff}.drawer{position:absolute;z-index:4;top:0;right:0;width:min(100%,500px);padding:22px;background:#fff;border:1px solid var(--border-subtle);border-radius:12px;box-shadow:0 16px 36px rgba(16,33,61,.16)}.drawer header{display:flex;justify-content:space-between;gap:16px;margin-bottom:18px}.drawer h3,.drawer p{margin:0}.drawer h3{font-size:1.1rem}.drawer p{margin-top:4px;color:var(--text-muted);font-size:.8rem}.drawer header button{border:0;background:transparent;color:var(--text-muted);font-size:1.5rem}@media(max-width:700px){.toolbar,.manager-header{align-items:flex-start;flex-direction:column}.primary-action{width:100%}.filter-tabs{width:100%;overflow:auto}.drawer{position:fixed;inset:auto 0 0;width:100%;border-radius:12px 12px 0 0}}
</style>
