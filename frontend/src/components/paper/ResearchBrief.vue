<script setup lang="ts">
import type { PaperAnalysis } from "../../api/paperAnalysis";
import ConfidenceBadge from "./ConfidenceBadge.vue";
import type { ConfidenceLevel } from "./paperModel";

/**
 * 中央顶部论文信息区：标题/作者来自 basic_information.value（真实字段）；
 * 期刊/年份/DOI 后端不存在 → 一律"未提供"；AI 状态与分析置信度概览真实展示。
 */
defineProps<{
  title: string | null;
  author: string | null;
  analysis: PaperAnalysis | null;
  confidence: ConfidenceLevel;
}>();

const UNAVAILABLE = "未提供";

const STATUS_LABELS: Record<PaperAnalysis["analysis_status"], string> = {
  pending: "等待分析",
  analyzing: "分析中",
  succeeded: "已完成",
  failed: "失败",
};
</script>

<template>
  <section class="brief" aria-label="论文信息">
    <div class="brief-main">
      <p class="eyebrow">AI RESEARCH REPORT</p>
      <h1 class="title">{{ title || UNAVAILABLE }}</h1>
      <p class="author">{{ author || UNAVAILABLE }}</p>
    </div>
    <dl class="meta">
      <div class="meta-item">
        <dt>期刊</dt>
        <dd>{{ UNAVAILABLE }}</dd>
      </div>
      <div class="meta-item">
        <dt>年份</dt>
        <dd>{{ UNAVAILABLE }}</dd>
      </div>
      <div class="meta-item">
        <dt>DOI</dt>
        <dd>{{ UNAVAILABLE }}</dd>
      </div>
    </dl>
    <div class="status-row">
      <span class="status-label">AI 分析状态</span>
      <span class="status-value" :class="`status-value--${analysis?.analysis_status ?? 'pending'}`">
        {{ analysis ? STATUS_LABELS[analysis.analysis_status] : "未生成" }}
      </span>
      <span class="divider" aria-hidden="true">·</span>
      <span class="status-label">置信度</span>
      <ConfidenceBadge :level="confidence" />
    </div>
  </section>
</template>

<style scoped>
.brief {
  display: grid;
  gap: 0.7rem;
  padding: 1.35rem 1.5rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  background: var(--surface);
  box-shadow: var(--shadow);
}
.brief-main {
  display: grid;
  gap: 0.25rem;
}
.eyebrow {
  margin: 0;
  color: var(--color-primary);
  font-size: 0.7rem;
  font-weight: 900;
  letter-spacing: 0.1em;
}
.title {
  margin: 0;
  font-size: 1.5rem;
  line-height: 1.25;
  color: var(--text-primary);
}
.author {
  margin: 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.4rem;
  margin: 0;
}
.meta-item {
  display: flex;
  gap: 0.4rem;
  font-size: 0.78rem;
}
.meta-item dt {
  color: var(--text-faint);
}
.meta-item dd {
  margin: 0;
  color: var(--text-muted);
}
.status-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding-top: 0.6rem;
  border-top: 1px solid var(--border-subtle);
  font-size: 0.78rem;
}
.status-label {
  color: var(--text-faint);
}
.status-value {
  font-weight: 750;
}
.status-value--succeeded {
  color: var(--color-success);
}
.status-value--analyzing,
.status-value--pending {
  color: var(--color-secondary);
}
.status-value--failed {
  color: var(--color-danger);
}
.divider {
  color: var(--border-strong);
}
</style>
