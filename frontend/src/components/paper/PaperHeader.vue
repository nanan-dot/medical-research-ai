<script setup lang="ts">
import { computed } from "vue";
import { paperAnalysisApi, type PaperAnalysis } from "../../api/paperAnalysis";

/**
 * 顶部工具栏：返回 / Analyze（重新生成）/ 创建组会汇报 / Export / More。
 * 创建组会汇报沿用 FE-06 前 UNAVAILABLE 文案；Export 沿用真实 exportUrl。
 */
const props = defineProps<{ analysis: PaperAnalysis | null; busy: boolean }>();

const emit = defineEmits<{
  back: [];
  regenerate: [];
  meeting: [];
  more: [];
}>();

/** 导出链接：仅当存在真实分析记录时可用，否则不渲染入口（后端未提供原文件打开） */
const exportUrl = computed<string | null>(() =>
  props.analysis?.id === undefined ? null : paperAnalysisApi.exportUrl(props.analysis.id),
);

function modelText(version: string | null | undefined): string {
  return version ? version : "未提供";
}
</script>

<template>
  <header class="toolbar">
    <button class="icon-button" type="button" aria-label="返回" @click="emit('back')">←</button>
    <button class="action-button" type="button" :disabled="busy || !analysis" @click="emit('regenerate')">
      {{ busy ? "分析中…" : "Analyze" }}
    </button>
    <button class="action-button" type="button" :disabled="busy" @click="emit('meeting')">
      创建组会汇报
    </button>
    <a v-if="exportUrl" class="action-button export-link" :href="exportUrl">导出 Markdown</a>
    <span class="spacer" />
    <span class="model">Model {{ modelText(analysis?.model_version) }}</span>
    <button class="icon-button" type="button" aria-label="更多操作" @click="emit('more')">⋯</button>
  </header>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.65rem 1rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.icon-button {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  font-size: 1.05rem;
  transition: background-color 0.15s, color 0.15s;
}
.icon-button:hover {
  background: var(--surface-muted);
  color: var(--text-primary);
}
.action-button {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-primary);
  font-weight: 750;
  transition: border-color 0.15s, background-color 0.15s;
}
.action-button:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.action-button:disabled {
  cursor: default;
  opacity: 0.55;
}
.export-link {
  text-decoration: none;
}
.spacer {
  flex: 1;
}
.model {
  color: var(--text-muted);
  font-size: 0.78rem;
  white-space: nowrap;
}
</style>
