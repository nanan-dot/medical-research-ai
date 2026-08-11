<script setup lang="ts">
import type { PaperAnalysis } from "../../api/paperAnalysis";

// 模板直接使用解构后的 props 字段（defineProps 无需显式赋值给变量）。
defineProps<{
  analysis: PaperAnalysis;
  title: string | null;
}>();

const STATUS_LABELS: Readonly<Record<PaperAnalysis["analysis_status"], string>> = {
  pending: "等待分析",
  analyzing: "分析中",
  succeeded: "分析完成",
  failed: "分析失败",
};

function evidenceText(count: number): string {
  return `原文证据 ${count} 条`;
}
</script>

<template>
  <section class="context-bar" aria-label="当前论文分析上下文">
    <div class="paper-identity">
      <span class="context-label">当前论文</span>
      <strong class="paper-title">{{ title || "未提供" }}</strong>
    </div>
    <div class="context-facts">
      <span>文档 ID {{ analysis.document_id }}</span>
      <span>{{ STATUS_LABELS[analysis.analysis_status] }}</span>
      <span>{{ evidenceText(analysis.sources.length) }}</span>
    </div>
  </section>
</template>

<style scoped>
.context-bar {
  display: flex;
  align-items: center;
  gap: 0.9rem 1.25rem;
  min-height: 2.9rem;
  padding: 0.6rem 0.85rem;
  border: 1px solid #d5e2f7;
  border-radius: var(--radius-md);
  background: #f8fbff;
}
.paper-identity {
  display: flex;
  align-items: baseline;
  gap: 0.45rem;
  min-width: 0;
}
.context-label,
.context-facts {
  color: var(--text-muted);
  font-size: 0.76rem;
}
.paper-title {
  min-width: 0;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 0.84rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.context-facts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.85rem;
}
.context-facts span + span::before {
  content: "·";
  margin-right: 0.85rem;
  color: var(--text-faint);
}
@media (max-width: 760px) {
  .context-bar {
    align-items: flex-start;
    flex-direction: column;
    gap: 0.35rem;
  }
}
</style>
