<script setup lang="ts">
import { computed } from "vue";
import { paperAnalysisApi, type PaperAnalysis } from "../../api/paperAnalysis";

/**
 * 单篇分析操作条只暴露真实能力：浏览器级返回、重生成和服务端导出。
 * 写作/汇报不属于当前研究页，因此不保留不可用的假入口。
 */
const props = defineProps<{ analysis: PaperAnalysis; busy: boolean }>();

const emit = defineEmits<{
  back: [];
  regenerate: [];
}>();

const exportUrl = computed(() => paperAnalysisApi.exportUrl(props.analysis.id));
</script>

<template>
  <header class="toolbar">
    <button class="back-button" type="button" aria-label="返回" @click="emit('back')">←</button>
    <button class="regenerate-button" type="button" :disabled="busy" @click="emit('regenerate')">
      {{ busy ? "分析中…" : "重新生成分析" }}
    </button>
    <a class="export-link" :href="exportUrl">导出 Markdown</a>
    <span class="model">Model {{ analysis.model_version || "未提供" }}</span>
  </header>
</template>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-height: 2.5rem;
}
.back-button,
.regenerate-button,
.export-link {
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text-primary);
  font-weight: 750;
  text-decoration: none;
}
.back-button {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  font-size: 1.05rem;
}
.regenerate-button,
.export-link {
  padding: 0.48rem 0.72rem;
  font-size: 0.8rem;
}
.regenerate-button {
  border-color: var(--color-primary);
  background: var(--color-primary);
  color: #fff;
}
.regenerate-button:disabled {
  opacity: 0.6;
}
.back-button:hover,
.export-link:hover {
  border-color: var(--color-primary);
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.model {
  margin-left: auto;
  color: var(--text-faint);
  font-size: 0.75rem;
  white-space: nowrap;
}
</style>
