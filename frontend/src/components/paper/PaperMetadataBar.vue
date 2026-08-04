<script setup lang="ts">
/**
 * 底部元数据条（Paper Metadata Bar）。
 * Study Type / Sample Size 来自真实结构化字段；Publication Date / Citation Count /
 * Evidence Level 后端无对应字段 → 一律"未提供"。不伪造任何统计数字。
 */
defineProps<{
  studyType: string | null;
  sampleSize: string | null;
  evidenceCount: number;
}>();

const UNAVAILABLE = "未提供";

function text(value: string | null): string {
  return value ? value : UNAVAILABLE;
}
</script>

<template>
  <footer class="meta-bar" aria-label="论文元数据">
    <dl class="meta-list">
      <div class="meta-item">
        <dt>Study Type</dt>
        <dd>{{ text(studyType) }}</dd>
      </div>
      <div class="meta-item">
        <dt>Sample Size</dt>
        <dd>{{ text(sampleSize) }}</dd>
      </div>
      <div class="meta-item">
        <dt>Publication Date</dt>
        <dd>{{ UNAVAILABLE }}</dd>
      </div>
      <div class="meta-item">
        <dt>Citation Count</dt>
        <dd>{{ UNAVAILABLE }}</dd>
      </div>
      <div class="meta-item">
        <dt>Evidence Level</dt>
        <dd>{{ UNAVAILABLE }}</dd>
      </div>
    </dl>
    <p class="evidence-note">Evidence 数量：{{ evidenceCount }}</p>
  </footer>
</template>

<style scoped>
.meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.75rem 1.35rem;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  background: var(--surface-muted);
}
.meta-list {
  display: flex;
  gap: 0.5rem 1.6rem;
  flex-wrap: wrap;
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
  color: var(--text-primary);
  font-weight: 700;
}
.evidence-note {
  margin: 0;
  font-size: 0.78rem;
  color: var(--text-muted);
}
</style>
