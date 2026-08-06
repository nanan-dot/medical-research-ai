<script setup lang="ts">
import { computed, shallowRef, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import ComparisonMatrix from "./ComparisonMatrix.vue";
import { createComparison, getComparison, regenerateComparison, updateComparisonCell } from "../../api/comparisons";
import type { ComparisonField, ComparisonTask } from "../../types/comparison";

const route = useRoute();
const router = useRouter();
const comparison = shallowRef<ComparisonTask | null>(null);
const documentIdsText = shallowRef("");
const error = shallowRef("");
const isLoading = shallowRef(false);
const isSaving = shallowRef(false);

const comparisonId = computed(() => {
  const rawId = route.query.id;
  const parsedId = typeof rawId === "string" ? Number(rawId) : Number.NaN;
  return Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null;
});

function parseDocumentIds(): number[] {
  return documentIdsText.value
    .split(",")
    .map((value) => Number(value.trim()))
    .filter((value) => Number.isInteger(value) && value > 0);
}

async function loadComparison() {
  if (comparisonId.value === null) {
    comparison.value = null;
    return;
  }
  isLoading.value = true;
  error.value = "";
  try {
    comparison.value = await getComparison(comparisonId.value);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法读取比较任务。";
  } finally {
    isLoading.value = false;
  }
}

async function createNewComparison() {
  const documentIds = parseDocumentIds();
  if (documentIds.length < 3 || new Set(documentIds).size !== documentIds.length) {
    error.value = "请输入 3 至 10 个不重复的文档 ID，以英文逗号分隔。";
    return;
  }
  isSaving.value = true;
  error.value = "";
  try {
    const task = await createComparison(documentIds);
    comparison.value = task;
    await router.replace({ path: "/comparisons", query: { id: task.id } });
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法创建比较任务。";
  } finally {
    isSaving.value = false;
  }
}

async function saveCell(documentId: number, field: ComparisonField, userValue: string) {
  if (comparison.value === null || !userValue.trim()) {
    return;
  }
  isSaving.value = true;
  error.value = "";
  try {
    comparison.value = await updateComparisonCell(comparison.value.id, documentId, field, userValue.trim());
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法保存人工修订。";
  } finally {
    isSaving.value = false;
  }
}

async function regenerate() {
  if (comparison.value === null) {
    return;
  }
  isSaving.value = true;
  error.value = "";
  try {
    comparison.value = await regenerateComparison(comparison.value.id);
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : "无法重新生成比较矩阵。";
  } finally {
    isSaving.value = false;
  }
}

function exportUrl(exportFormat: "csv" | "markdown"): string | null {
  if (comparison.value === null) {
    return null;
  }
  return `/api/v1/comparisons/${comparison.value.id}/export?format=${exportFormat}`;
}

watch(comparisonId, loadComparison, { immediate: true });
</script>

<template>
  <main class="comparison-view">
    <header class="page-header">
      <p class="eyebrow">MULTI-PAPER COMPARISON · LIVE</p>
      <h1 class="page-title">多论文比较</h1>
      <p class="page-copy">矩阵仅显示后端返回的可追溯单元格；缺失值不会被自动推断。人工修订会保留，重新生成不会覆盖它们。</p>
    </header>

    <form class="create-form" @submit.prevent="createNewComparison">
      <label class="form-label" for="document-ids">文档 ID</label>
      <input id="document-ids" v-model="documentIdsText" class="document-input" inputmode="numeric" placeholder="例如：12, 15, 18" :disabled="isSaving" />
      <button type="submit" :disabled="isSaving">创建比较</button>
    </form>

    <p v-if="error" class="request-error" role="alert">{{ error }}</p>
    <p v-if="isLoading" class="state-text">正在读取比较任务…</p>
    <p v-else-if="comparison === null" class="empty-state">输入至少三篇已保存文档的 ID 后创建比较。页面不会填充演示论文或医学结论。</p>

    <section v-else class="comparison-workspace" aria-label="比较矩阵工作区">
      <div class="toolbar">
        <span>比较任务 #{{ comparison.id }} · {{ comparison.selected_document_ids.length }} 篇论文</span>
        <button :disabled="isSaving" @click="regenerate">重新生成未编辑单元格</button>
        <a v-if="exportUrl('csv')" :href="exportUrl('csv')!">导出 CSV</a>
        <a v-if="exportUrl('markdown')" :href="exportUrl('markdown')!">导出 Markdown</a>
      </div>
      <ComparisonMatrix :comparison="comparison" :is-saving="isSaving" @save-cell="saveCell" />
    </section>
  </main>
</template>

<style scoped>
.comparison-view { display: grid; gap: 1rem; max-width: 1440px; margin: auto; padding: 2rem 1.4rem 3rem; }
.eyebrow { margin: 0; color: var(--color-primary); font-size: .72rem; font-weight: 800; letter-spacing: .12em; }
.page-title { margin: .25rem 0; color: var(--text-primary); font-size: clamp(2rem, 4vw, 3.2rem); }
.page-copy { max-width: 760px; margin: 0; color: var(--text-muted); line-height: 1.6; }
.create-form { display: flex; align-items: end; flex-wrap: wrap; gap: .7rem; padding: 1rem; border: 1px solid var(--border-subtle); border-radius: var(--radius-md); background: var(--surface); }
.form-label { display: grid; gap: .35rem; color: var(--text-muted); font-size: .82rem; font-weight: 700; }
.document-input { min-width: min(100%, 320px); padding: .55rem .7rem; border: 1px solid var(--border-strong); border-radius: 8px; color: var(--text-primary); background: var(--paper); }
.create-form button, .toolbar button, .toolbar a { padding: .55rem .8rem; border: 1px solid var(--border-strong); border-radius: 8px; color: var(--text-primary); background: var(--paper); font: inherit; font-weight: 700; text-decoration: none; }
.create-form button, .toolbar button { cursor: pointer; }
.create-form button:disabled, .toolbar button:disabled { cursor: wait; opacity: .6; }
.request-error { margin: 0; padding: .8rem; color: var(--color-danger); background: var(--color-danger-soft); border-radius: var(--radius-md); }
.state-text, .empty-state { margin: 0; padding: 1.2rem; color: var(--text-muted); }
.empty-state { border: 1px dashed var(--border-strong); border-radius: var(--radius-md); text-align: center; }
.comparison-workspace { display: grid; gap: .8rem; }
.toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: .6rem; color: var(--text-muted); font-size: .86rem; }
.toolbar span { margin-right: auto; }
@media (max-width: 640px) { .comparison-view { padding: 1.25rem .85rem 2rem; } .create-form { align-items: stretch; } .document-input { width: 100%; } .toolbar span { width: 100%; } }
</style>
