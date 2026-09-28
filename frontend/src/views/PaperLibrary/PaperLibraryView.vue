<script setup lang="ts">
import { computed, onBeforeUnmount, shallowRef, watch } from "vue";
import { useRoute, useRouter, type LocationQueryRaw } from "vue-router";

import {
  DEFAULT_PAPER_FILTERS,
  paperLibraryApi,
  type AnalysisStatus,
  type PaperAddRequest,
  type PaperFilters,
  type PaperItem,
  type PaperOverview as PaperOverviewModel,
  type PaperSort,
  type PaperView,
  type ReadingStatus,
  type ResearchRole,
} from "../../api/paperLibrary";
import type { ResourceImportItem } from "../../api/resourceLibrary";
import AddPaperDialog from "../../components/paper-library/AddPaperDialog.vue";
import LibraryPaperPickerDialog from "../../components/paper-library/LibraryPaperPickerDialog.vue";
import PaperFilterRail, { type PaperFilterGroupKey } from "../../components/paper-library/PaperFilterRail.vue";
import PaperLibraryHeader from "../../components/paper-library/PaperLibraryHeader.vue";
import PaperOverview from "../../components/paper-library/PaperOverview.vue";
import PaperQuickViews from "../../components/paper-library/PaperQuickViews.vue";
import PaperResearchRelationDialog from "../../components/paper-library/PaperResearchRelationDialog.vue";
import PaperUploadDialog from "../../components/paper-library/PaperUploadDialog.vue";
import PaperWorkList from "../../components/paper-library/PaperWorkList.vue";
import PaperWorkToolbar, { type PaperFilterChip } from "../../components/paper-library/PaperWorkToolbar.vue";
import { analysisLabel, readingLabel, roleLabel } from "../../components/paper-library/paperLibraryFormatters";
import { usePaperLibrary } from "../../composables/usePaperLibrary";
import { usePaperOverview } from "../../composables/usePaperOverview";

const route = useRoute();
const router = useRouter();
const library = usePaperLibrary();
const overview = usePaperOverview();
const selectedId = shallowRef<number | null>(null);
const overviewOpen = shallowRef(false);
const filterOpen = shallowRef(false);
const density = shallowRef<"comfortable" | "compact">("comfortable");
const addDialogOpen = shallowRef(false);
const pickerOpen = shallowRef(false);
const uploadOpen = shallowRef(false);
const relationDialogOpen = shallowRef(false);
const addPending = shallowRef(false);
const actionPending = shallowRef(false);
const addError = shallowRef<string | null>(null);
const toast = shallowRef<string | null>(null);
let searchTimer: ReturnType<typeof setTimeout> | null = null;
let toastTimer: ReturnType<typeof setTimeout> | null = null;
let routeSequence = 0;

const selectedOverview = computed(() => overview.paper.value);
const activeChips = computed<PaperFilterChip[]>(() => {
  const chips: PaperFilterChip[] = [];
  library.filters.readingStatus.forEach((value) => chips.push({ key: `readingStatus:${value}`, label: readingLabel(value) }));
  library.filters.analysisStatus.forEach((value) => chips.push({ key: `analysisStatus:${value}`, label: analysisLabel(value) }));
  library.filters.researchRoles.forEach((value) => chips.push({ key: `researchRoles:${value}`, label: roleLabel(value) }));
  library.filters.paperTypes.forEach((value) => chips.push({ key: `paperTypes:${value}`, label: library.facets.value?.paper_types.find((item) => item.value === value)?.label ?? value }));
  library.filters.researchIds.forEach((value) => chips.push({ key: `researchIds:${value}`, label: library.facets.value?.research_contexts.find((item) => item.value === String(value))?.label ?? `研究 ${value}` }));
  library.filters.tags.forEach((value) => chips.push({ key: `tags:${value}`, label: value }));
  return chips;
});

function values(name: string): string[] {
  const raw = route.query[name];
  const source = Array.isArray(raw) ? raw : raw == null ? [] : [raw];
  return source.flatMap((item) => typeof item === "string" ? item.split(",") : []).map((item) => item.trim()).filter(Boolean);
}

function validValues<T extends string>(input: readonly string[], allowed: readonly T[]): T[] {
  const accepted = new Set<string>(allowed);
  return input.filter((item): item is T => accepted.has(item));
}

function routeFilters(): PaperFilters {
  const view = validValues(values("view"), ["all", "recent", "reading", "analyzing", "unclassified"] as const)[0] ?? "all";
  const sort = validValues(values("sort"), ["recent_activity", "added_at", "year", "title"] as const)[0] ?? "recent_activity";
  return {
    view,
    sort,
    query: typeof route.query.q === "string" ? route.query.q.slice(0, 300) : "",
    readingStatus: validValues(values("reading_status"), ["unread", "reading", "read"] as const),
    analysisStatus: validValues(values("analysis_status"), ["not_started", "pending", "analyzing", "completed", "failed", "cancelled"] as const),
    paperTypes: values("paper_type"),
    researchRoles: validValues(values("research_role"), ["core_evidence", "background_support", "method_reference", "supplementary_reading", "to_evaluate"] as const),
    researchIds: values("research_id").map(Number).filter((item) => Number.isInteger(item) && item > 0),
    tags: values("tag"),
  };
}

function positiveInteger(value: unknown): number | null {
  const parsed = typeof value === "string" ? Number(value) : Number.NaN;
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function queryFor(filters: Readonly<PaperFilters>, page = 1, paperId: number | null = selectedId.value, showOverview = overviewOpen.value): LocationQueryRaw {
  return {
    ...(filters.view !== "all" ? { view: filters.view } : {}), ...(filters.query ? { q: filters.query } : {}),
    ...(filters.sort !== "recent_activity" ? { sort: filters.sort } : {}),
    ...(filters.readingStatus.length ? { reading_status: [...filters.readingStatus] } : {}),
    ...(filters.analysisStatus.length ? { analysis_status: [...filters.analysisStatus] } : {}),
    ...(filters.paperTypes.length ? { paper_type: [...filters.paperTypes] } : {}),
    ...(filters.researchRoles.length ? { research_role: [...filters.researchRoles] } : {}),
    ...(filters.researchIds.length ? { research_id: filters.researchIds.map(String) } : {}),
    ...(filters.tags.length ? { tag: [...filters.tags] } : {}), ...(page > 1 ? { page: String(page) } : {}),
    ...(paperId ? { paper_id: String(paperId) } : {}), ...(showOverview ? { overview: "1" } : {}),
  };
}

async function applyRoute(): Promise<void> {
  const sequence = ++routeSequence;
  const nextFilters = routeFilters();
  const page = Math.max(1, positiveInteger(route.query.page) ?? 1);
  await library.load(nextFilters, (page - 1) * library.pageSize);
  if (sequence !== routeSequence) return;
  const requestedId = positiveInteger(route.query.paper_id);
  const nextId = library.items.value.some((item) => item.id === requestedId) ? requestedId : library.items.value[0]?.id ?? null;
  selectedId.value = nextId;
  const explicitOverview = route.query.overview === "1";
  overviewOpen.value = explicitOverview || (route.query.overview !== "0" && globalThis.innerWidth >= 1024);
  if (nextId) await overview.load(nextId); else overview.clear();
}

function updateFilters(next: Partial<PaperFilters>, page = 1): void {
  const filters: PaperFilters = { ...library.filters, ...next, readingStatus: [...(next.readingStatus ?? library.filters.readingStatus)], analysisStatus: [...(next.analysisStatus ?? library.filters.analysisStatus)], paperTypes: [...(next.paperTypes ?? library.filters.paperTypes)], researchRoles: [...(next.researchRoles ?? library.filters.researchRoles)], researchIds: [...(next.researchIds ?? library.filters.researchIds)], tags: [...(next.tags ?? library.filters.tags)] };
  void router.replace({ query: queryFor(filters, page, null, false) });
}

function setView(view: PaperView): void { filterOpen.value = false; updateFilters({ view }); }
function setSort(sort: PaperSort): void { updateFilters({ sort }); }
function toggleFilter(group: PaperFilterGroupKey, rawValue: string): void {
  if (group === "researchIds") { const value = Number(rawValue); const current = library.filters.researchIds; updateFilters({ researchIds: current.includes(value) ? current.filter((item) => item !== value) : [...current, value] }); return; }
  if (group === "readingStatus") { const value = rawValue as ReadingStatus; const current = library.filters.readingStatus; updateFilters({ readingStatus: current.includes(value) ? current.filter((item) => item !== value) : [...current, value] }); return; }
  if (group === "analysisStatus") { const value = rawValue as AnalysisStatus; const current = library.filters.analysisStatus; updateFilters({ analysisStatus: current.includes(value) ? current.filter((item) => item !== value) : [...current, value] }); return; }
  if (group === "researchRoles") { const value = rawValue as ResearchRole; const current = library.filters.researchRoles; updateFilters({ researchRoles: current.includes(value) ? current.filter((item) => item !== value) : [...current, value] }); return; }
  const current = group === "paperTypes" ? library.filters.paperTypes : library.filters.tags;
  updateFilters({ [group]: current.includes(rawValue) ? current.filter((item) => item !== rawValue) : [...current, rawValue] });
}

function clearFilters(): void { updateFilters({ ...DEFAULT_PAPER_FILTERS, view: library.filters.view, query: library.filters.query, sort: library.filters.sort }); }
function removeChip(key: string): void { const [group, value] = key.split(":", 2); toggleFilter(group as PaperFilterGroupKey, value); }
function search(query: string): void { if (searchTimer) clearTimeout(searchTimer); searchTimer = setTimeout(() => updateFilters({ query }), 280); }

function selectPaper(id: number): void {
  selectedId.value = id; overviewOpen.value = true; void overview.load(id);
  void router.replace({ query: queryFor(library.filters, library.page.value, id, true) });
}

function activatePaper(paper: PaperItem): void { openReading(paper); }
function openReading(paper: PaperItem): void { if (paper.reading_entry.enabled && paper.document_id) void router.push({ path: `/paper-research/${paper.id}`, query: { from: "papers" } }); }
function openResource(paper: PaperItem): void { if (paper.document_id) void router.push({ path: `/documents/${paper.document_id}`, query: { from: "papers" } }); }
function morePaper(paper: PaperItem): void { selectPaper(paper.id); }

function notify(message: string): void { toast.value = message; if (toastTimer) clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.value = null; }, 3200); }
function openIdentifiers(): void { addError.value = null; addDialogOpen.value = true; }
function openPicker(): void { addError.value = null; pickerOpen.value = true; }
function openUpload(): void { addDialogOpen.value = false; uploadOpen.value = true; }

async function addPaper(payload: PaperAddRequest, source: "identifier" | "library" = "identifier"): Promise<void> {
  addPending.value = true; addError.value = null;
  try {
    const result = await paperLibraryApi.add(payload);
    addDialogOpen.value = false; pickerOpen.value = false;
    await library.load(routeFilters(), 0); selectedId.value = result.item.id; overviewOpen.value = true; await overview.load(result.item.id);
    void router.replace({ query: queryFor(library.filters, 1, result.item.id, true) });
    notify(result.outcome === "already_exists" ? "论文已在论文库中，已为你定位" : source === "library" ? "已从资料库加入论文库" : "论文已加入，元数据将按真实状态显示");
  } catch (cause) { addError.value = cause instanceof Error ? cause.message : "论文暂时无法添加"; }
  finally { addPending.value = false; }
}

async function handleUploaded(items: ResourceImportItem[]): Promise<void> {
  try {
    const documentIds = items.flatMap((item) => item.document_id ? [item.document_id] : []);
    if (!documentIds.length) { notify("上传结果中没有可加入论文库的 PDF"); return; }
    const results = await Promise.allSettled(documentIds.map((documentId) => paperLibraryApi.add({ document_id: documentId })));
    const succeeded = results.filter((item) => item.status === "fulfilled").length;
    await library.load(routeFilters(), 0);
    notify(succeeded === documentIds.length ? `已将 ${succeeded} 篇 PDF 加入论文库` : `已加入 ${succeeded} 篇，${documentIds.length - succeeded} 篇未能加入`);
  } catch (cause) {
    notify(cause instanceof Error ? cause.message : "上传后无法刷新论文库");
  }
}

async function refreshMetadata(paper: PaperOverviewModel): Promise<void> {
  actionPending.value = true;
  try { await paperLibraryApi.refreshMetadata(paper.id); await Promise.all([library.load(routeFilters(), library.offset.value), overview.load(paper.id)]); notify("论文元数据已按上游结果更新"); }
  catch (cause) { notify(cause instanceof Error ? cause.message : "元数据更新失败"); }
  finally { actionPending.value = false; }
}

async function relationChanged(): Promise<void> {
  relationDialogOpen.value = false;
  if (selectedId.value) await Promise.all([library.load(routeFilters(), library.offset.value), overview.load(selectedId.value)]);
  notify("研究关联已更新");
}

watch(() => route.fullPath, () => void applyRoute(), { immediate: true });
onBeforeUnmount(() => { library.cancel(); overview.cancel(); if (searchTimer) clearTimeout(searchTimer); if (toastTimer) clearTimeout(toastTimer); });
</script>

<template>
  <main class="paper-library-page">
    <PaperLibraryHeader :query="library.filters.query" :loading="library.loading.value" @search="search" @add-from-library="openPicker" @import-paper="openIdentifiers" @open-filters="filterOpen = true" />
    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
    <p v-if="library.error.value" class="library-error" role="alert"><span>{{ library.error.value }}</span><button type="button" @click="applyRoute">重试</button></p>
    <div class="library-workspace" :class="{ 'overview-closed': !overviewOpen }">
      <PaperFilterRail :open="filterOpen" :filters="library.filters" :facets="library.facets.value" @close="filterOpen = false" @clear="clearFilters" @view="setView" @toggle="toggleFilter" />
      <section class="center-pane">
        <PaperQuickViews :active="library.filters.view" :summary="library.summary.value" @select="setView" />
        <PaperWorkToolbar :chips="activeChips" :total="library.total.value" :sort="library.filters.sort" :density="density" :refreshing="library.isRefreshing.value" @remove="removeChip" @clear="clearFilters" @sort="setSort" @density="density = $event" @open-filters="filterOpen = true" />
        <PaperWorkList :items="library.items.value" :total="library.total.value" :selected-id="selectedId" :loading="library.loading.value" :initialized="library.initialized.value" :page="library.page.value" :page-count="library.pageCount.value" :has-previous="library.hasPrevious.value" :has-next="library.hasNext.value" :density="density" @select="selectPaper" @activate="activatePaper" @read="openReading" @more="morePaper" @previous="updateFilters({}, Math.max(1, library.page.value - 1))" @next="updateFilters({}, library.page.value + 1)" />
      </section>
      <PaperOverview :open="overviewOpen" :paper="selectedOverview" :loading="overview.loading.value" :error="overview.error.value" :action-pending="actionPending" @close="overviewOpen = false; router.replace({ query: queryFor(library.filters, library.page.value, selectedId, false) })" @retry="selectedId && overview.load(selectedId)" @read="openReading" @resource="openResource" @edit-relations="relationDialogOpen = true" @refresh-metadata="refreshMetadata" />
    </div>
    <AddPaperDialog :open="addDialogOpen" :pending="addPending" :error="addError" @close="addDialogOpen = false" @upload="openUpload" @submit="addPaper" />
    <LibraryPaperPickerDialog :open="pickerOpen" :pending="addPending" :error="addError" @close="pickerOpen = false" @select="addPaper({ document_id: $event }, 'library')" />
    <PaperUploadDialog :open="uploadOpen" @close="uploadOpen = false" @imported="handleUploaded" />
    <PaperResearchRelationDialog :open="relationDialogOpen" :paper="selectedOverview" @close="relationDialogOpen = false" @changed="relationChanged" />
  </main>
</template>

<style scoped>
:global(.shell:has(.paper-library-page)){--app-sidebar-expanded-width:192px}:global(.shell:has(.paper-library-page) .topbar){display:none!important}:global(.shell:has(.paper-library-page) .content){min-height:100vh}.paper-library-page{min-height:100vh;background:#f7f9fc;color:#0f172a}.library-workspace{display:grid;grid-template-columns:196px minmax(560px,1fr) 368px;height:calc(100vh - 80px);min-height:720px;margin-right:14px;overflow:hidden;background:#fff}.library-workspace.overview-closed{grid-template-columns:196px minmax(560px,1fr)}.library-workspace.overview-closed>:deep(.overview-layer){display:none}.center-pane{min-width:0;height:100%;overflow:auto;background:#fff}.library-error{position:absolute;z-index:35;top:80px;right:0;left:0;display:flex;align-items:center;justify-content:center;gap:12px;margin:0;padding:8px 14px;border-bottom:1px solid #fecaca;background:#fff1f2;color:#c52b2f;font-size:12px}.library-error button{border:0;background:transparent;color:inherit;font:inherit;font-weight:700;text-decoration:underline}.toast{position:fixed;z-index:70;top:18px;left:50%;padding:9px 14px;border:1px solid #bbf7d0;border-radius:5px;background:#f0fdf4;color:#087a55;font-size:12px;font-weight:650;box-shadow:0 5px 18px rgb(15 23 42 / 10%);transform:translateX(-50%)}
@media(max-width:1439px) and (min-width:1280px){.library-workspace{grid-template-columns:208px minmax(560px,1fr) 312px}.library-workspace.overview-closed{grid-template-columns:208px minmax(560px,1fr)}}
@media(min-width:1024px) and (max-width:1279px){.library-workspace{grid-template-columns:minmax(0,1fr) 300px;margin-right:0}.library-workspace.overview-closed{grid-template-columns:minmax(0,1fr)}.library-workspace>:deep(.filter-layer){display:none}.library-workspace>:deep(.filter-layer.open){display:block}}
@media(max-width:1023px){.library-workspace,.library-workspace.overview-closed{grid-template-columns:minmax(0,1fr);margin-right:0}.library-workspace>:deep(.filter-layer){display:none}.library-workspace>:deep(.filter-layer.open){display:block}}
@media(max-width:900px){.library-workspace{height:calc(100vh - 157px);min-height:560px}}
@media(max-width:767px){.paper-library-page{min-height:100vh}.library-workspace{height:auto;min-height:calc(100vh - 149px);overflow:visible}.center-pane{height:auto;overflow:visible}}
</style>
