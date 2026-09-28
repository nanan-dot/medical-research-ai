<script setup lang="ts">
import { nextTick, onBeforeUnmount, reactive, ref, watch } from "vue";

import type { ResourceLibraryFacets, ResourceLibraryFilters } from "../../api/resourceLibrary";

const props = defineProps<{
  filters: {
    readonly query: string;
    readonly sourceIds: readonly number[];
    readonly nodeId: string | null;
    readonly fileTypes: readonly ResourceLibraryFilters["fileTypes"][number][];
    readonly statuses: readonly ResourceLibraryFilters["statuses"][number][];
    readonly updatedFrom: string | null;
    readonly updatedTo: string | null;
    readonly sortBy: ResourceLibraryFilters["sortBy"];
    readonly sortOrder: ResourceLibraryFilters["sortOrder"];
  };
  facets: Readonly<ResourceLibraryFacets> | null;
  disabled: boolean;
}>();
const emit = defineEmits<{ change: [filters: ResourceLibraryFilters] }>();

const draft = reactive<ResourceLibraryFilters>({ ...props.filters, sourceIds: [...props.filters.sourceIds], fileTypes: [...props.filters.fileTypes], statuses: [...props.filters.statuses] });
const isDrawerOpen = ref(false);
const drawer = ref<HTMLElement | null>(null);
let searchTimer: ReturnType<typeof setTimeout> | null = null;
let opener: HTMLElement | null = null;

watch(() => props.filters, (filters) => {
  Object.assign(draft, { ...filters, sourceIds: [...filters.sourceIds], fileTypes: [...filters.fileTypes], statuses: [...filters.statuses] });
}, { deep: true });

function current(): ResourceLibraryFilters {
  return {
    ...draft,
    query: draft.query.trim(),
    sourceIds: [...draft.sourceIds],
    fileTypes: [...draft.fileTypes],
    statuses: [...draft.statuses],
  };
}

function submit(): void {
  emit("change", current());
}

function scheduleSearch(): void {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(submit, 300);
}

function clearFilters(): void {
  Object.assign(draft, { query: "", sourceIds: [], nodeId: null, fileTypes: [], statuses: [], updatedFrom: null, updatedTo: null, sortBy: "updated_at", sortOrder: "desc" });
  submit();
}

function openDrawer(event: MouseEvent): void {
  opener = event.currentTarget instanceof HTMLElement ? event.currentTarget : null;
  isDrawerOpen.value = true;
  void nextTick(() => drawer.value?.focus());
}

function closeDrawer(): void {
  isDrawerOpen.value = false;
  void nextTick(() => opener?.focus());
}

function onDrawerKeydown(event: KeyboardEvent): void {
  if (event.key === "Escape") closeDrawer();
}

function facetLabel(value: string, fallback: string): string {
  const labels: Readonly<Record<string, string>> = {
    ai_available: "AI 可使用",
    processing: "处理中",
    needs_processing: "待处理",
    needs_attention: "需处理",
    outdated: "内容已更新",
    metadata_only: "仅元数据",
  };
  return labels[value] ?? fallback;
}

onBeforeUnmount(() => {
  if (searchTimer) clearTimeout(searchTimer);
});
</script>

<template>
  <section class="document-filters" aria-label="资料筛选工具栏">
    <div class="search-row">
      <label class="search-input" for="resource-library-query">
        <span class="sr-only">搜索资料标题、正文内容、路径或来源</span><span aria-hidden="true">⌕</span>
        <input id="resource-library-query" v-model="draft.query" :disabled="props.disabled" placeholder="搜索资料标题、正文内容、路径或来源…" @input="scheduleSearch" @keydown.enter.prevent="submit">
      </label>
      <button class="search-button" type="button" :disabled="props.disabled" @click="submit">搜索</button>
    </div>

    <div class="filter-row">
      <label class="filter-control"><span>来源</span><select v-model="draft.sourceIds" multiple :disabled="props.disabled" aria-label="按资料来源筛选" @change="submit"><option v-for="facet in props.facets?.sources ?? []" :key="facet.value" :value="Number(facet.value)">{{ facet.value }} ({{ facet.count }})</option></select></label>
      <label class="filter-control"><span>类型</span><select v-model="draft.fileTypes" multiple :disabled="props.disabled" aria-label="按资料类型筛选" @change="submit"><option v-for="facet in props.facets?.file_types ?? []" :key="facet.value" :value="facet.value">{{ facet.value.toUpperCase() }} ({{ facet.count }})</option></select></label>
      <label class="filter-control"><span>状态</span><select v-model="draft.statuses" multiple :disabled="props.disabled" aria-label="按资料状态筛选" @change="submit"><option v-for="facet in props.facets?.statuses ?? []" :key="facet.value" :value="facet.value">{{ facetLabel(facet.value, facet.value) }} ({{ facet.count }})</option></select></label>
      <label class="filter-control date-control"><span>更新时间</span><input v-model="draft.updatedFrom" type="date" :disabled="props.disabled" aria-label="更新时间开始" @change="submit"></label>
      <label class="filter-control"><span>排序</span><select v-model="draft.sortBy" :disabled="props.disabled" @change="submit"><option value="updated_at">最近更新</option><option value="name">资料名称</option><option value="file_size">文件大小</option><option value="source_name">来源</option><option value="status">状态</option><option value="last_opened">最近打开</option></select></label>
      <button class="sort-order" type="button" :disabled="props.disabled" :aria-label="draft.sortOrder === 'desc' ? '切换为升序' : '切换为降序'" @click="draft.sortOrder = draft.sortOrder === 'desc' ? 'asc' : 'desc'; submit()">{{ draft.sortOrder === "desc" ? "↓" : "↑" }}</button>
      <button class="more-filters" type="button" :aria-expanded="isDrawerOpen" :disabled="props.disabled" @click="openDrawer">筛选</button>
      <button v-if="draft.query || draft.sourceIds.length || draft.fileTypes.length || draft.statuses.length || draft.updatedFrom || draft.updatedTo" class="clear" type="button" :disabled="props.disabled" @click="clearFilters">清除全部</button>
    </div>
  </section>

  <Teleport to="body">
    <div v-if="isDrawerOpen" class="filter-drawer-layer" @click.self="closeDrawer">
      <aside ref="drawer" class="filter-drawer" role="dialog" aria-modal="true" aria-labelledby="resource-filter-title" tabindex="-1" @keydown="onDrawerKeydown">
        <header><h2 id="resource-filter-title">全部筛选</h2><button type="button" aria-label="关闭全部筛选" @click="closeDrawer">×</button></header>
        <label>开始日期<input v-model="draft.updatedFrom" type="date"></label>
        <label>结束日期<input v-model="draft.updatedTo" type="date"></label>
        <footer><button type="button" @click="clearFilters">清除全部</button><button class="apply" type="button" @click="submit(); closeDrawer()">应用筛选</button></footer>
      </aside>
    </div>
  </Teleport>
</template>

<style scoped>
.document-filters { padding:12px 14px; border-bottom:1px solid var(--border-subtle); background:var(--elevated, #fbfcfe); }.search-row,.filter-row { display:flex; align-items:center; gap:8px; }.search-input { display:flex; flex:1; align-items:center; gap:8px; min-width:180px; height:36px; padding:0 10px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); color:var(--text-faint); }.search-input:focus-within { border-color:var(--color-primary); box-shadow:0 0 0 2px var(--color-primary-soft); }.search-input input { min-width:0; width:100%; border:0; outline:0; background:transparent; color:var(--text-primary); font:inherit; font-size:13px; }.search-button,.more-filters,.sort-order { min-height:34px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); color:var(--text-primary); font:inherit; font-size:12px; font-weight:700; cursor:pointer; }.search-button { border-color:var(--color-primary); padding:0 12px; background:var(--color-primary); color:#fff; }.filter-row { flex-wrap:wrap; margin-top:8px; }.filter-control { display:flex; align-items:center; gap:5px; min-height:30px; padding:0 7px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); color:var(--text-muted); font-size:11px; font-weight:700; }.filter-control select { max-width:120px; min-width:56px; border:0; outline:0; background:transparent; color:var(--text-primary); font:inherit; font-size:12px; }.filter-control select[multiple] { height:24px; }.filter-control input { width:108px; border:0; outline:0; background:transparent; color:var(--text-primary); font:inherit; font-size:12px; }.sort-order { width:34px; }.more-filters { padding:0 10px; }.clear { border:0; background:transparent; color:var(--color-primary); font:inherit; font-size:12px; font-weight:700; cursor:pointer; }.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0,0,0,0); white-space:nowrap; }.filter-drawer-layer { position:fixed; z-index:50; inset:0; display:flex; justify-content:flex-end; background:rgb(15 23 42 / 28%); }.filter-drawer { width:min(400px, 100vw); height:100%; padding:20px; background:var(--surface); box-shadow:var(--shadow-md, -8px 0 24px rgb(15 23 42 / 8%)); outline:0; }.filter-drawer header,.filter-drawer footer { display:flex; align-items:center; justify-content:space-between; gap:12px; }.filter-drawer h2 { margin:0; font-size:16px; }.filter-drawer header button,.filter-drawer footer button { min-height:36px; border:1px solid var(--border-subtle); border-radius:4px; background:var(--surface); color:var(--text-primary); font:inherit; cursor:pointer; }.filter-drawer > label { display:grid; gap:6px; margin-top:18px; color:var(--text-muted); font-size:13px; font-weight:650; }.filter-drawer input { min-height:36px; border:1px solid var(--border-subtle); border-radius:4px; padding:0 8px; font:inherit; }.filter-drawer footer { margin-top:24px; }.filter-drawer footer .apply { padding:0 12px; border-color:var(--color-primary); background:var(--color-primary); color:#fff; }@media(max-width:767px){.document-filters{padding:10px 12px}.filter-row{overflow-x:auto;flex-wrap:nowrap;padding-bottom:2px}.filter-control{flex:0 0 auto}.search-button{display:none}.filter-drawer{width:100%;height:auto;min-height:60vh;margin-top:auto;border-radius:8px 8px 0 0;}}@media(prefers-reduced-motion:reduce){.filter-drawer-layer{transition:none}}
</style>
