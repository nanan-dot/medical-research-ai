<script setup lang="ts">
import type { ConfidenceLevel } from "./paperModel";

/** 置信度三态徽章：标签与配色均为常量，不与后端字段硬绑定 */
defineProps<{ level: ConfidenceLevel }>();

const LABELS: Record<ConfidenceLevel, string> = {
  high: "High",
  medium: "Medium",
  "needs-verification": "Needs verification",
};

const A11Y: Record<ConfidenceLevel, string> = {
  high: "高置信度",
  medium: "中置信度",
  "needs-verification": "待验证",
};
</script>

<template>
  <span class="badge" :class="`badge--${level}`" :aria-label="A11Y[level]">{{ LABELS[level] }}</span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.16rem 0.5rem;
  border-radius: 99px;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.02em;
  white-space: nowrap;
}
.badge::before {
  content: "";
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 99px;
  background: currentColor;
  opacity: 0.85;
}
.badge--high {
  background: var(--color-success-soft);
  color: var(--color-success);
}
.badge--medium {
  background: var(--color-primary-soft);
  color: var(--color-primary);
}
.badge--needs-verification {
  background: var(--color-warning-soft);
  color: var(--color-warning);
}
</style>
